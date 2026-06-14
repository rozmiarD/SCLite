from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from sclite._json import load_json_object
from sclite.artifacts import build_artifact_hash, validate_artifact

CHAIN_CANONICALIZATION_VERSION = 'sclite-artifact-chain-v0.2'
CHAIN_HASH_ALGORITHM = 'sha256'
V02_LIFECYCLE_ROLES = (
    'intent_contract',
    'policy_decision',
    'execution_contract',
    'execution_ticket',
    'execution_receipt',
    'evidence_contract',
)
CONSUMABLE_TICKET_APPROVAL_STATUSES = {'approved_for_dry_run', 'approved'}
TERMINAL_TICKET_APPROVAL_STATUSES = {'rejected', 'expired', 'revoked'}


class ChainVerificationError(ValueError):
    """Raised when an artifact-chain manifest does not match its payloads."""


@dataclass(frozen=True)
class ChainArtifactInput:
    role: str
    path: str
    value: Mapping[str, Any]
    required: bool = True


def _schema_ref(value: Mapping[str, Any]) -> str:
    raw = value.get('schema_ref') or value.get('schema') or ''
    return str(raw)


def _schema_version(value: Mapping[str, Any]) -> str:
    raw = value.get('schema_version') or value.get('spec_version') or value.get('version') or ''
    return str(raw)


def artifact_descriptor(value: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a v0.2 descriptor for one JSON-compatible artifact.

    The descriptor is intentionally content-addressing only. It proves that a
    verifier saw the same canonical payload bytes; it does not prove signer
    identity, legal authority, or runtime enforcement.
    """
    digest = build_artifact_hash(dict(value))
    return {
        'artifact_type': str(value.get('artifact_type') or ''),
        'schema_version': _schema_version(value),
        'schema_ref': _schema_ref(value),
        'canonicalization': digest['canonicalization'],
        'algorithm': digest['algorithm'],
        'digest': digest['digest'],
        'canonical_bytes': digest['canonical_bytes'],
    }


def _chain_step(previous_chain_digest: str, role: str, descriptor: Mapping[str, Any]) -> str:
    payload = {
        'previous_chain_digest': previous_chain_digest,
        'role': role,
        'artifact_digest': descriptor['digest'],
        'artifact_type': descriptor.get('artifact_type', ''),
        'canonicalization': descriptor.get('canonicalization', ''),
        'algorithm': descriptor.get('algorithm', ''),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def _coerce_inputs(artifacts: Iterable[Mapping[str, Any]]) -> List[ChainArtifactInput]:
    result: List[ChainArtifactInput] = []
    for item in artifacts:
        value = item.get('value')
        if not isinstance(value, Mapping):
            raise TypeError('artifact chain inputs require mapping value fields')
        result.append(ChainArtifactInput(
            role=str(item.get('role') or value.get('artifact_type') or ''),
            path=str(item.get('path') or ''),
            value=value,
            required=bool(item.get('required', True)),
        ))
    return result


def build_artifact_chain_manifest(
    artifacts: Iterable[Mapping[str, Any]],
    *,
    chain_id: str = 'sclite-v0.2-lifecycle-chain',
    created_at: str = '1970-01-01T00:00:00+00:00',
    profile: str = 'sclite-v0.2-integrity-only',
) -> Dict[str, Any]:
    """Build an ordered hash-linked v0.2 chain manifest.

    This is the lightweight v0.2 crypto core: mandatory tamper-evident content
    binding with no PKI dependency. Signature/authenticity layers can bind to
    the manifest root digest later without changing artifact payload shapes.
    """
    previous = ''
    entries: List[Dict[str, Any]] = []
    for item in _coerce_inputs(artifacts):
        descriptor = artifact_descriptor(item.value)
        chain_digest = _chain_step(previous, item.role, descriptor)
        entries.append({
            'role': item.role,
            'path': item.path,
            'required': item.required,
            'descriptor': descriptor,
            'previous_chain_digest': previous,
            'chain_digest': chain_digest,
        })
        previous = chain_digest
    return {
        'artifact_type': 'artifact_chain_manifest',
        'schema_version': 'v0.2',
        'schema_ref': 'schemas/artifact_chain_manifest.v0.2.schema.json',
        'chain_id': chain_id,
        'created_at': created_at,
        'profile': profile,
        'canonicalization': CHAIN_CANONICALIZATION_VERSION,
        'hash_algorithm': CHAIN_HASH_ALGORITHM,
        'signature_policy': {
            'mode': 'integrity_only',
            'identity_signature_required': False,
            'note': 'v0.2 core verifies tamper-evident artifact binding; signer identity is an optional runtime/profile concern.',
        },
        'entries': entries,
        'root_chain_digest': previous,
    }


def _load_json_object(path: Path) -> Dict[str, Any]:
    return load_json_object(path, error_cls=ChainVerificationError)


def _link_descriptor(value: Mapping[str, Any], link_name: str) -> Mapping[str, Any]:
    links = value.get('links')
    if not isinstance(links, Mapping):
        raise ChainVerificationError(f'{value.get("artifact_type") or "artifact"} has no links object')
    link = links.get(link_name)
    if not isinstance(link, Mapping):
        raise ChainVerificationError(f'{value.get("artifact_type") or "artifact"} missing links.{link_name}')
    descriptor = link.get('descriptor')
    if not isinstance(descriptor, Mapping):
        raise ChainVerificationError(f'{value.get("artifact_type") or "artifact"} missing links.{link_name}.descriptor')
    return descriptor


def _assert_link_binds(source: Mapping[str, Any], link_name: str, target: Mapping[str, Any], reason: str) -> None:
    expected = artifact_descriptor(target)
    actual = dict(_link_descriptor(source, link_name))
    if actual != expected:
        raise ChainVerificationError(reason)


def _mapping_field(value: Mapping[str, Any], key: str, label: str) -> Mapping[str, Any]:
    item = value.get(key)
    if not isinstance(item, Mapping):
        raise ChainVerificationError(f'{label} missing {key} object')
    return item


def verify_lifecycle_semantics(artifacts_by_role: Mapping[str, Mapping[str, Any]]) -> List[str]:
    """Verify v0.2 lifecycle semantics beyond hash-chain integrity.

    This checks the contract lifecycle bindings that matter operationally:
    the ticket must bind the execution contract digest, the receipt must bind
    the ticket digest, the evidence contract must bind the receipt digest, and
    the canonical roles must appear in order. It remains local/static; it does
    not execute tools, prove legal authorization, or prove signer identity.
    """
    roles = tuple(artifacts_by_role.keys())
    if roles != V02_LIFECYCLE_ROLES:
        raise ChainVerificationError(f'lifecycle role order mismatch: expected {list(V02_LIFECYCLE_ROLES)}, got {list(roles)}')

    intent = artifacts_by_role['intent_contract']
    policy = artifacts_by_role['policy_decision']
    contract = artifacts_by_role['execution_contract']
    ticket = artifacts_by_role['execution_ticket']
    receipt = artifacts_by_role['execution_receipt']
    evidence = artifacts_by_role['evidence_contract']

    _assert_link_binds(policy, 'intent', intent, 'policy-intent digest mismatch')
    policy_decision = str(policy.get('decision') or '')
    approval = _mapping_field(ticket, 'approval', 'execution_ticket')
    approval_status = str(approval.get('status') or '')
    if policy_decision == 'deny':
        raise ChainVerificationError('policy decision denies executable lifecycle')
    if policy_decision == 'owner_approval_required' and approval_status not in CONSUMABLE_TICKET_APPROVAL_STATUSES:
        raise ChainVerificationError('owner approval required before executable lifecycle')
    if approval_status in TERMINAL_TICKET_APPROVAL_STATUSES:
        raise ChainVerificationError(f'execution ticket approval is terminal: {approval_status}')
    if approval_status not in CONSUMABLE_TICKET_APPROVAL_STATUSES:
        raise ChainVerificationError(f'execution ticket is not approved for executable lifecycle: {approval_status or "missing"}')

    _assert_link_binds(contract, 'intent', intent, 'execution_contract-intent digest mismatch')
    _assert_link_binds(contract, 'policy_decision', policy, 'execution_contract-policy digest mismatch')
    _assert_link_binds(ticket, 'execution_contract', contract, 'ticket-execution_contract digest mismatch')

    integrity = ticket.get('integrity')
    if not isinstance(integrity, Mapping):
        raise ChainVerificationError('execution_ticket missing integrity object')
    bound_digest = str(integrity.get('ticket_binds_execution_contract_digest') or '')
    contract_digest = artifact_descriptor(contract)['digest']
    if bound_digest != contract_digest:
        raise ChainVerificationError('ticket integrity execution_contract digest mismatch')

    _assert_link_binds(receipt, 'execution_ticket', ticket, 'receipt-ticket digest mismatch')
    _assert_link_binds(receipt, 'execution_contract', contract, 'receipt-execution_contract digest mismatch')
    _assert_link_binds(evidence, 'execution_receipt', receipt, 'evidence-receipt digest mismatch')
    _assert_link_binds(evidence, 'execution_ticket', ticket, 'evidence-ticket digest mismatch')

    return [
        'role_order',
        'policy_binds_intent',
        'contract_binds_intent_and_policy',
        'ticket_binds_execution_contract',
        'receipt_binds_execution_ticket',
        'receipt_binds_execution_contract',
        'evidence_binds_execution_receipt',
        'evidence_binds_execution_ticket',
    ]


def _raise_lifecycle_roles_mismatch(checked: Sequence[str]) -> None:
    raise ChainVerificationError(
        f'lifecycle roles mismatch: expected {list(V02_LIFECYCLE_ROLES)}, got {list(checked)}'
    )


def verify_artifact_chain_manifest(
    manifest: Mapping[str, Any],
    *,
    root: Path | None = None,
    validate_schemas: bool = True,
    strict_jsonschema: bool = False,
    require_lifecycle: bool = False,
) -> Dict[str, Any]:
    """Verify manifest descriptors and hash links against local artifact files."""
    entries = manifest.get('entries')
    if not isinstance(entries, list):
        raise ChainVerificationError('manifest.entries is not an array')
    base = (root or Path.cwd()).resolve()
    previous = ''
    checked: List[str] = []
    artifacts_by_role: Dict[str, Mapping[str, Any]] = {}
    duplicate_roles: List[str] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            raise ChainVerificationError(f'entry[{index}] is not an object')
        role = str(entry.get('role') or '')
        rel_path = str(entry.get('path') or '')
        if not rel_path:
            raise ChainVerificationError(f'entry[{index}] has empty path')
        artifact_path = (base / rel_path).resolve()
        try:
            artifact_path.relative_to(base)
        except ValueError as exc:
            raise ChainVerificationError(f'entry[{index}] path escapes root: {rel_path}') from exc
        value = _load_json_object(artifact_path)
        if validate_schemas:
            schema_ref = _schema_ref(value)
            if schema_ref:
                validate_artifact(value, schema_ref, root=base, strict_jsonschema=strict_jsonschema)
        expected_descriptor = entry.get('descriptor')
        actual_descriptor = artifact_descriptor(value)
        if expected_descriptor != actual_descriptor:
            raise ChainVerificationError(f'entry[{index}] descriptor mismatch for {rel_path}')
        expected_previous = str(entry.get('previous_chain_digest') or '')
        if expected_previous != previous:
            raise ChainVerificationError(f'entry[{index}] previous_chain_digest mismatch')
        actual_chain_digest = _chain_step(previous, role, actual_descriptor)
        if str(entry.get('chain_digest') or '') != actual_chain_digest:
            raise ChainVerificationError(f'entry[{index}] chain_digest mismatch')
        previous = actual_chain_digest
        checked.append(role)
        if role in artifacts_by_role:
            duplicate_roles.append(role)
        else:
            artifacts_by_role[role] = value
    if str(manifest.get('root_chain_digest') or '') != previous:
        raise ChainVerificationError('root_chain_digest mismatch')
    semantic_checks: List[str] = []
    checked_roles = tuple(checked)
    if require_lifecycle and checked_roles != V02_LIFECYCLE_ROLES:
        _raise_lifecycle_roles_mismatch(checked)
    if require_lifecycle and checked_roles == V02_LIFECYCLE_ROLES:
        semantic_checks = verify_lifecycle_semantics(artifacts_by_role)
    lifecycle_status = 'passed' if require_lifecycle else 'not_checked'
    return {
        'status': 'passed',
        'chain_status': 'passed',
        'lifecycle_status': lifecycle_status,
        'checked_entries': checked,
        'entry_count': len(checked),
        'root_chain_digest': previous,
        'semantic_checks': semantic_checks,
        'canonicalization': manifest.get('canonicalization') or CHAIN_CANONICALIZATION_VERSION,
        'hash_algorithm': manifest.get('hash_algorithm') or CHAIN_HASH_ALGORITHM,
    }


def verify_lifecycle_manifest(
    manifest: Mapping[str, Any],
    *,
    root: Path | None = None,
    validate_schemas: bool = True,
    strict_jsonschema: bool = False,
) -> Dict[str, Any]:
    """Verify a v0.2 lifecycle manifest with fail-safe lifecycle semantics."""

    return verify_artifact_chain_manifest(
        manifest,
        root=root,
        validate_schemas=validate_schemas,
        strict_jsonschema=strict_jsonschema,
        require_lifecycle=True,
    )
