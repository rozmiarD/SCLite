from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from sclite._json import (
    DEFAULT_VERIFICATION_LIMITS,
    VerificationLimits,
    _JsonBudget,
    load_json_document,
    load_json_object,
    validate_json_value,
)
from sclite.artifacts import build_artifact_hash, validate_artifact
from sclite.errors import SCLiteValidationError

CHAIN_CANONICALIZATION_VERSION = 'sclite-artifact-chain-v0.2'
CHAIN_HASH_ALGORITHM = 'sha256'
CHAIN_MANIFEST_SCHEMA_REF = 'schemas/artifact_chain_manifest.v0.2.schema.json'
SUPPORTED_CHAIN_MANIFEST_PROFILES = frozenset({
    'sclite-v0.2-integrity-only',
    'sclite-v0.5-bad-cross-host-integrity',
    'sclite-v0.5-govengine-integration-integrity',
    'sclite-v0.5-rexecop-integrity',
    'sclite-v0.5-review-bundle-integrity-only',
    'sclite-v0.6-alpha-local-admin-change',
    'sclite-reaction-v0.1',
})
V02_LIFECYCLE_ROLES = (
    'intent_contract',
    'policy_decision',
    'execution_contract',
    'execution_ticket',
    'execution_receipt',
    'evidence_contract',
)
V02_LIFECYCLE_ROLE_SCHEMAS = {
    'intent_contract': (('v0.2', 'schemas/intent_contract.v0.2.schema.json'),),
    'policy_decision': (
        ('v0.2', 'schemas/policy_decision.v0.2.schema.json'),
        ('v0.3', 'schemas/policy_decision.v0.3.schema.json'),
    ),
    'execution_contract': (
        ('v0.2', 'schemas/execution_contract.v0.2.schema.json'),
        ('v0.3', 'schemas/execution_contract.v0.3.schema.json'),
    ),
    'execution_ticket': (
        ('v0.2', 'schemas/execution_ticket.v0.2.schema.json'),
        ('v0.3', 'schemas/execution_ticket.v0.3.schema.json'),
    ),
    'execution_receipt': (('v0.2', 'schemas/execution_receipt.v0.2.schema.json'),),
    'evidence_contract': (('v0.2', 'schemas/evidence_contract.v0.2.schema.json'),),
}
CONSUMABLE_TICKET_APPROVAL_STATUSES = {'approved_for_dry_run', 'approved'}
TERMINAL_TICKET_APPROVAL_STATUSES = {'rejected', 'expired', 'revoked'}


class ChainVerificationError(SCLiteValidationError):
    """Raised when an artifact-chain manifest does not match its payloads."""

    default_code = 'chain_verification_failed'


@dataclass(frozen=True)
class ChainArtifactInput:
    role: str
    path: str
    value: Mapping[str, Any]
    required: bool = True


class _FrozenDict(dict[str, Any]):
    """A private JSON mapping that rejects accidental mutation after loading."""

    @staticmethod
    def _immutable(*_args: Any, **_kwargs: Any) -> None:
        raise TypeError('verified snapshot values are immutable')

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    setdefault = _immutable
    update = _immutable

    def popitem(self) -> tuple[str, Any]:
        self._immutable()
        raise AssertionError('unreachable')

    def __ior__(self, _other: object) -> '_FrozenDict':  # type: ignore[override,misc]
        self._immutable()
        raise AssertionError('unreachable')


class _FrozenList(list[Any]):
    """A private JSON sequence that rejects accidental mutation after loading."""

    @staticmethod
    def _immutable(*_args: Any, **_kwargs: Any) -> None:
        raise TypeError('verified snapshot values are immutable')

    __setitem__ = _immutable
    __delitem__ = _immutable
    append = _immutable
    clear = _immutable
    extend = _immutable
    insert = _immutable
    pop = _immutable
    remove = _immutable
    reverse = _immutable
    sort = _immutable

    def __iadd__(self, _values: Iterable[Any]) -> '_FrozenList':  # type: ignore[misc]
        self._immutable()
        raise AssertionError('unreachable')

    def __imul__(self, _value: object) -> '_FrozenList':
        self._immutable()
        raise AssertionError('unreachable')


def _freeze_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        frozen = _FrozenDict()
        for key, item in value.items():
            dict.__setitem__(frozen, str(key), _freeze_json_value(item))
        return frozen
    if isinstance(value, list):
        frozen_list = _FrozenList()
        list.extend(frozen_list, (_freeze_json_value(item) for item in value))
        return frozen_list
    return value


@dataclass(frozen=True)
class _ArtifactSnapshot:
    """One descriptor-verified payload used by all layers of one verification."""

    role: str
    relative_path: str
    raw_bytes: bytes
    value: Mapping[str, Any]
    descriptor: Mapping[str, Any]


@dataclass(frozen=True)
class _VerifiedBundleSnapshot:
    """Private immutable handoff for layered SCLite verification paths."""

    artifacts_by_role: Mapping[str, _ArtifactSnapshot]


def _load_artifact_snapshot(
    path: Path,
    *,
    role: str,
    relative_path: str,
    max_bytes: int | None = None,
    limits: VerificationLimits | None = None,
    budget: _JsonBudget | None = None,
) -> _ArtifactSnapshot:
    raw_bytes, parsed = load_json_document(
        path,
        error_cls=ChainVerificationError,
        max_bytes=max_bytes,
        limits=limits,
        budget=budget,
    )
    if not isinstance(parsed, dict):
        raise ChainVerificationError(f'{path}: JSON root is not an object')
    descriptor = artifact_descriptor(parsed)
    frozen_value = _freeze_json_value(parsed)
    if not isinstance(frozen_value, Mapping):  # pragma: no cover - parser root guard
        raise ChainVerificationError(f'{path}: JSON root is not an object')
    return _ArtifactSnapshot(
        role=role,
        relative_path=relative_path,
        raw_bytes=raw_bytes,
        value=frozen_value,
        descriptor=MappingProxyType(dict(descriptor)),
    )


def _validate_manifest_identity(
    manifest: Mapping[str, Any],
    *,
    root: Path | None,
    strict_jsonschema: bool,
) -> None:
    """Reject manifests whose declared identity cannot match this verifier."""

    try:
        validate_artifact(
            dict(manifest),
            CHAIN_MANIFEST_SCHEMA_REF,
            root=root,
            strict_jsonschema=strict_jsonschema,
        )
    except (AssertionError, ValueError) as exc:
        raise ChainVerificationError(f'manifest schema validation failed:{exc}') from exc

    profile = str(manifest.get('profile') or '')
    if profile not in SUPPORTED_CHAIN_MANIFEST_PROFILES:
        raise ChainVerificationError(f'unsupported manifest profile: {profile or "missing"}')
    signature_policy = manifest.get('signature_policy')
    if not isinstance(signature_policy, Mapping):
        raise ChainVerificationError('manifest signature_policy is not an object')
    if str(signature_policy.get('mode') or '') != 'integrity_only':
        raise ChainVerificationError('unsupported manifest signature_policy.mode')
    if signature_policy.get('identity_signature_required') is not False:
        raise ChainVerificationError('unsupported manifest signature_policy.identity_signature_required')


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


def _load_json_object(path: Path, *, max_bytes: int | None = None) -> Dict[str, Any]:
    return load_json_object(path, error_cls=ChainVerificationError, max_bytes=max_bytes)


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


def _lifecycle_role_summary(checked: Sequence[str], duplicate_roles: Sequence[str]) -> Dict[str, Any]:
    seen = set(checked)
    expected = set(V02_LIFECYCLE_ROLES)
    extra_roles = sorted(role for role in seen if role not in expected)
    missing_roles = [role for role in V02_LIFECYCLE_ROLES if role not in seen]
    return {
        'status': 'canonical' if tuple(checked) == V02_LIFECYCLE_ROLES else 'noncanonical',
        'expected_roles': list(V02_LIFECYCLE_ROLES),
        'missing_roles': missing_roles,
        'extra_roles': extra_roles,
        'duplicate_roles': sorted(set(duplicate_roles)),
    }


def _assert_strict_lifecycle_artifact_shapes(artifacts_by_role: Mapping[str, Mapping[str, Any]]) -> List[str]:
    checks: List[str] = []
    for role in V02_LIFECYCLE_ROLES:
        artifact = artifacts_by_role[role]
        artifact_type = str(artifact.get('artifact_type') or '')
        if artifact_type != role:
            raise ChainVerificationError(f'{role} artifact_type mismatch: expected {role}, got {artifact_type or "missing"}')
        schema_version = _schema_version(artifact)
        schema_ref = _schema_ref(artifact)
        allowed = V02_LIFECYCLE_ROLE_SCHEMAS[role]
        if (schema_version, schema_ref) not in allowed:
            allowed_text = ', '.join(f'{version}:{ref}' for version, ref in allowed)
            actual_text = f'{schema_version or "missing"}:{schema_ref or "missing"}'
            raise ChainVerificationError(f'{role} schema identity mismatch: expected one of {allowed_text}, got {actual_text}')
        checks.append(f'{role}_schema_identity')
    return checks


def _legacy_lifecycle_scope_status(
    artifacts_by_role: Mapping[str, Mapping[str, Any]],
) -> tuple[str, str]:
    """Evaluate the legacy boolean scope assertion without claiming authority."""

    policy_scope = _mapping_field(
        artifacts_by_role['policy_decision'],
        'scope',
        'policy_decision',
    )
    target_binding = _mapping_field(
        artifacts_by_role['execution_contract'],
        'target_binding',
        'execution_contract',
    )
    policy_value = policy_scope.get('target_in_scope')
    contract_value = target_binding.get('target_in_scope')
    if policy_value is False or contract_value is False:
        raise ChainVerificationError('lifecycle target_in_scope is explicitly false')
    if policy_value is not True or contract_value is not True:
        return (
            'not_checked',
            'legacy target_in_scope assertion is missing or unknown',
        )
    return (
        'operator_asserted',
        'legacy target_in_scope assertions agree; authority authentication is not checked',
    )


def _lifecycle_scope_status(
    artifacts_by_role: Mapping[str, Mapping[str, Any]],
) -> tuple[str, str]:
    policy = artifacts_by_role['policy_decision']
    contract = artifacts_by_role['execution_contract']
    if _schema_version(policy) != 'v0.3' or _schema_version(contract) != 'v0.3':
        return _legacy_lifecycle_scope_status(artifacts_by_role)
    policy_assertion = _mapping_field(policy, 'scope_assertion', 'policy_decision')
    contract_assertion = _mapping_field(contract, 'scope_assertion', 'execution_contract')
    authority_decision = _mapping_field(policy, 'authority_decision', 'policy_decision')
    if dict(policy_assertion) != dict(contract_assertion):
        raise ChainVerificationError('scope assertion differs between policy and execution contract')
    expected_digest = 'sha256:' + str(artifact_descriptor(authority_decision)['digest'])
    if str(policy_assertion.get('decision_digest') or '') != expected_digest:
        raise ChainVerificationError('scope assertion authority decision digest mismatch')
    for field in ('status', 'authority', 'decision_ref', 'subject', 'target'):
        if policy_assertion.get(field) != authority_decision.get(field):
            raise ChainVerificationError(f'scope assertion authority decision {field} mismatch')
    target = _mapping_field(policy_assertion, 'target', 'scope_assertion')
    policy_scope = _mapping_field(policy, 'scope', 'policy_decision')
    target_binding = _mapping_field(contract, 'target_binding', 'execution_contract')
    if target.get('target_host') != policy_scope.get('target_host'):
        raise ChainVerificationError('scope assertion policy target mismatch')
    if target.get('target_host') != target_binding.get('target_host'):
        raise ChainVerificationError('scope assertion execution target_host mismatch')
    if target.get('target') != target_binding.get('target'):
        raise ChainVerificationError('scope assertion execution target mismatch')
    status = str(policy_assertion.get('status') or '')
    if status == 'out_of_scope':
        raise ChainVerificationError('scope assertion is explicitly out_of_scope')
    if status != 'in_scope':
        return 'not_checked', 'scope assertion is unknown'
    return (
        'authority_artifact_bound',
        'scope assertion is digest-bound; authority authentication is not checked',
    )


def _lifecycle_ticket_validity_status(
    artifacts_by_role: Mapping[str, Mapping[str, Any]],
) -> tuple[str, str]:
    """Reuse the ticket interval check for every strict lifecycle version."""

    # This import is deliberately local: tickets consumes the public descriptor
    # helper from this module, while strict lifecycle must also validate v0.2
    # ticket/receipt pairs that do not use the v0.3 ticket-use profile.
    from sclite.tickets import (
        TicketSemanticError,
        TicketUseVerificationError,
        _receipt_within_ticket_window_status,
    )

    receipt = artifacts_by_role['execution_receipt']
    outcome = _mapping_field(receipt, 'outcome', 'execution_receipt')
    try:
        return _receipt_within_ticket_window_status(
            artifacts_by_role['execution_ticket'],
            receipt,
            receipt_status=str(outcome.get('status') or '').lower(),
        )
    except (TicketSemanticError, TicketUseVerificationError) as exc:
        raise ChainVerificationError(str(exc)) from exc


def _verify_artifact_chain_manifest_with_snapshot(
    manifest: Mapping[str, Any],
    *,
    root: Path | None = None,
    validate_schemas: bool = True,
    strict_jsonschema: bool = False,
    require_lifecycle: bool = False,
    max_artifact_bytes: int | None = None,
    max_manifest_entries: int | None = None,
    verification_limits: VerificationLimits | None = None,
) -> tuple[Dict[str, Any], _VerifiedBundleSnapshot]:
    """Verify one bundle and retain the private snapshot for layered checks."""
    base = (root or Path.cwd()).resolve()
    limits = verification_limits or DEFAULT_VERIFICATION_LIMITS
    budget = _JsonBudget(limits)
    validate_json_value(
        manifest,
        source='artifact_chain_manifest',
        error_cls=ChainVerificationError,
        limits=limits,
        budget=budget,
    )
    _validate_manifest_identity(
        manifest,
        root=base,
        strict_jsonschema=strict_jsonschema,
    )
    entries = manifest.get('entries')
    if not isinstance(entries, list):
        raise ChainVerificationError('manifest.entries is not an array')
    entry_limit = max_manifest_entries or limits.max_manifest_entries
    if len(entries) > entry_limit:
        raise ChainVerificationError(f'manifest entry count exceeds max_manifest_entries={entry_limit}')
    previous = ''
    checked: List[str] = []
    artifacts_by_role: Dict[str, _ArtifactSnapshot] = {}
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
        normalized_rel_path = artifact_path.relative_to(base).as_posix()
        artifact = _load_artifact_snapshot(
            artifact_path,
            role=role,
            relative_path=normalized_rel_path,
            max_bytes=max_artifact_bytes,
            limits=limits,
            budget=budget,
        )
        value = artifact.value
        if validate_schemas:
            schema_ref = _schema_ref(value)
            if schema_ref:
                validate_artifact(value, schema_ref, root=base, strict_jsonschema=strict_jsonschema)
        expected_descriptor = entry.get('descriptor')
        actual_descriptor = artifact.descriptor
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
            artifacts_by_role[role] = artifact
    if str(manifest.get('root_chain_digest') or '') != previous:
        raise ChainVerificationError('root_chain_digest mismatch')
    semantic_checks: List[str] = []
    scope_status = 'not_checked'
    scope_detail = 'scope is not checked for integrity-only verification'
    ticket_validity_status = 'not_checked'
    ticket_validity_detail = 'ticket validity is not checked for integrity-only verification'
    checked_roles = tuple(checked)
    role_summary = _lifecycle_role_summary(checked, duplicate_roles)
    if require_lifecycle and checked_roles != V02_LIFECYCLE_ROLES:
        _raise_lifecycle_roles_mismatch(checked)
    if require_lifecycle and checked_roles == V02_LIFECYCLE_ROLES:
        semantic_artifacts = {
            role: artifact.value for role, artifact in artifacts_by_role.items()
        }
        semantic_checks = _assert_strict_lifecycle_artifact_shapes(semantic_artifacts)
        semantic_checks.extend(verify_lifecycle_semantics(semantic_artifacts))
        scope_status, scope_detail = _lifecycle_scope_status(semantic_artifacts)
        ticket_validity_status, ticket_validity_detail = _lifecycle_ticket_validity_status(
            semantic_artifacts,
        )
        if scope_status == 'operator_asserted':
            semantic_checks.append('target_in_scope_legacy_assertion')
        if scope_status == 'authority_artifact_bound':
            semantic_checks.append('scope_authority_artifact_binding')
        if ticket_validity_status == 'passed':
            semantic_checks.append('receipt_within_ticket_validity')
    lifecycle_status = (
        'passed'
        if (
            require_lifecycle
            and scope_status in {'operator_asserted', 'authority_artifact_bound'}
            and ticket_validity_status == 'passed'
        )
        else 'review'
        if require_lifecycle
        else 'not_checked'
    )
    verification_posture = 'strict_lifecycle' if require_lifecycle else 'integrity_only'
    result = {
        'status': 'passed' if lifecycle_status != 'review' else 'review',
        'chain_status': 'passed',
        'lifecycle_status': lifecycle_status,
        'verification_posture': verification_posture,
        'checked_entries': checked,
        'entry_count': len(checked),
        'root_chain_digest': previous,
        'semantic_checks': semantic_checks,
        'lifecycle_role_summary': role_summary,
        'scope_status': scope_status,
        'scope_detail': scope_detail,
        'scope_authority_authenticated': 'not_checked',
        'ticket_validity_status': ticket_validity_status,
        'ticket_validity_detail': ticket_validity_detail,
        'canonicalization': CHAIN_CANONICALIZATION_VERSION,
        'hash_algorithm': CHAIN_HASH_ALGORITHM,
    }
    snapshot = _VerifiedBundleSnapshot(
        artifacts_by_role=MappingProxyType(dict(artifacts_by_role)),
    )
    return result, snapshot


def verify_artifact_chain_manifest(
    manifest: Mapping[str, Any],
    *,
    root: Path | None = None,
    validate_schemas: bool = True,
    strict_jsonschema: bool = False,
    require_lifecycle: bool = False,
    max_artifact_bytes: int | None = None,
    max_manifest_entries: int | None = None,
    verification_limits: VerificationLimits | None = None,
) -> Dict[str, Any]:
    """Verify manifest descriptors and hash links against local artifact files."""

    result, _snapshot = _verify_artifact_chain_manifest_with_snapshot(
        manifest,
        root=root,
        validate_schemas=validate_schemas,
        strict_jsonschema=strict_jsonschema,
        require_lifecycle=require_lifecycle,
        max_artifact_bytes=max_artifact_bytes,
        max_manifest_entries=max_manifest_entries,
        verification_limits=verification_limits,
    )
    return result


def verify_lifecycle_manifest(
    manifest: Mapping[str, Any],
    *,
    root: Path | None = None,
    validate_schemas: bool = True,
    strict_jsonschema: bool = False,
    verification_limits: VerificationLimits | None = None,
) -> Dict[str, Any]:
    """Verify a v0.2 lifecycle manifest with fail-safe lifecycle semantics."""

    return verify_artifact_chain_manifest(
        manifest,
        root=root,
        validate_schemas=validate_schemas,
        strict_jsonschema=strict_jsonschema,
        require_lifecycle=True,
        max_artifact_bytes=None,
        max_manifest_entries=None,
        verification_limits=verification_limits,
    )
