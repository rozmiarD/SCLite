from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from sclite.artifacts import ARTIFACT_CANONICALIZATION_VERSION, ARTIFACT_HASH_ALGORITHM, build_artifact_hash, validate_artifact

CHAIN_CANONICALIZATION_VERSION = 'sclite-artifact-chain-v0.2'
CHAIN_HASH_ALGORITHM = 'sha256'


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
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ChainVerificationError(f'{path}: JSON root is not an object')
    return value


def verify_artifact_chain_manifest(manifest: Mapping[str, Any], *, root: Path | None = None, validate_schemas: bool = True) -> Dict[str, Any]:
    """Verify manifest descriptors and hash links against local artifact files."""
    entries = manifest.get('entries')
    if not isinstance(entries, list):
        raise ChainVerificationError('manifest.entries is not an array')
    base = (root or Path.cwd()).resolve()
    previous = ''
    checked: List[str] = []
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
                validate_artifact(value, schema_ref, root=base)
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
    if str(manifest.get('root_chain_digest') or '') != previous:
        raise ChainVerificationError('root_chain_digest mismatch')
    return {
        'status': 'passed',
        'checked_entries': checked,
        'entry_count': len(checked),
        'root_chain_digest': previous,
        'canonicalization': manifest.get('canonicalization') or CHAIN_CANONICALIZATION_VERSION,
        'hash_algorithm': manifest.get('hash_algorithm') or CHAIN_HASH_ALGORITHM,
    }
