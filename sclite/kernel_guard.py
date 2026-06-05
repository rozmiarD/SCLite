from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from typing import Any, Dict, Mapping, Sequence

from .artifacts import validate_artifact
from .integrity import ChainVerificationError, verify_artifact_chain_manifest

KERNEL_GUARD_PROFILE = 'kernel_guard_hmac_v1'
KERNEL_GUARD_ENTRY_PROFILE = 'kernel_guard_hmac_v1.entry'
KERNEL_GUARD_ROOT_PROFILE = 'kernel_guard_hmac_v1.root'
KERNEL_GUARD_ALGORITHM = 'hmac-sha256'
KERNEL_GUARD_SCHEMA_REF = 'schemas/kernel_guard_hmac_v1.schema.json'


class KernelGuardError(ValueError):
    """Raised when a kernel guard sidecar does not authenticate a manifest."""


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def _key_bytes(key: str | bytes) -> bytes:
    if isinstance(key, bytes):
        return key
    return str(key).encode('utf-8')


def _sha256_hex(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _hmac_hex(key: str | bytes, value: Mapping[str, Any]) -> str:
    return hmac.new(_key_bytes(key), _canonical_bytes(value), hashlib.sha256).hexdigest()


def manifest_metadata_digest(manifest: Mapping[str, Any]) -> str:
    """Digest manifest metadata without entries, root digest, or embedded guard."""

    metadata = {
        str(key): value
        for key, value in manifest.items()
        if key not in {'entries', 'root_chain_digest', 'kernel_guard'}
    }
    return _sha256_hex(metadata)


def _entries(manifest: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    entries = manifest.get('entries')
    if not isinstance(entries, list) or not all(isinstance(item, Mapping) for item in entries):
        raise KernelGuardError('manifest.entries is not an array of objects')
    return entries


def _descriptor(entry: Mapping[str, Any]) -> Mapping[str, Any]:
    descriptor = entry.get('descriptor')
    if not isinstance(descriptor, Mapping):
        raise KernelGuardError('manifest entry missing descriptor')
    return descriptor


def _entry_transcript(
    manifest: Mapping[str, Any],
    entry: Mapping[str, Any],
    *,
    seq: int,
    entry_count: int,
    previous_tag: str,
    nonce: str,
    key_id: str,
) -> Dict[str, Any]:
    descriptor = _descriptor(entry)
    return {
        'profile': KERNEL_GUARD_ENTRY_PROFILE,
        'chain_id': str(manifest.get('chain_id') or ''),
        'seq': seq,
        'entry_count': entry_count,
        'role': str(entry.get('role') or ''),
        'path': str(entry.get('path') or ''),
        'required': bool(entry.get('required', False)),
        'artifact_digest': str(descriptor.get('digest') or ''),
        'artifact_type': str(descriptor.get('artifact_type') or ''),
        'schema_ref': str(descriptor.get('schema_ref') or ''),
        'schema_version': str(descriptor.get('schema_version') or ''),
        'canonicalization': str(descriptor.get('canonicalization') or ''),
        'algorithm': str(descriptor.get('algorithm') or ''),
        'previous_tag': previous_tag,
        'nonce': nonce,
        'key_id': key_id,
    }


def _root_transcript(
    manifest: Mapping[str, Any],
    *,
    entry_count: int,
    first_tag: str,
    last_tag: str,
    key_id: str,
) -> Dict[str, Any]:
    return {
        'profile': KERNEL_GUARD_ROOT_PROFILE,
        'chain_id': str(manifest.get('chain_id') or ''),
        'entry_count': entry_count,
        'first_tag': first_tag,
        'last_tag': last_tag,
        'root_chain_digest': str(manifest.get('root_chain_digest') or ''),
        'manifest_metadata_digest': manifest_metadata_digest(manifest),
        'key_id': key_id,
    }


def build_kernel_guard_manifest(
    manifest: Mapping[str, Any],
    *,
    key: str | bytes,
    key_id: str,
    nonces: Sequence[str] | None = None,
) -> Dict[str, Any]:
    """Build a sidecar HMAC guard for an already-built artifact-chain manifest."""

    entries = _entries(manifest)
    if nonces is not None and len(nonces) != len(entries):
        raise KernelGuardError('nonce count must match manifest entry count')
    previous_tag = ''
    entry_guards = []
    for seq, entry in enumerate(entries):
        nonce = str(nonces[seq]) if nonces is not None else secrets.token_hex(16)
        transcript = _entry_transcript(
            manifest,
            entry,
            seq=seq,
            entry_count=len(entries),
            previous_tag=previous_tag,
            nonce=nonce,
            key_id=key_id,
        )
        tag = _hmac_hex(key, transcript)
        entry_guards.append({**transcript, 'tag': tag})
        previous_tag = tag

    first_tag = str(entry_guards[0]['tag']) if entry_guards else ''
    last_tag = previous_tag
    root_transcript = _root_transcript(
        manifest,
        entry_count=len(entries),
        first_tag=first_tag,
        last_tag=last_tag,
        key_id=key_id,
    )
    root_tag = _hmac_hex(key, root_transcript)
    return {
        'artifact_type': 'kernel_guard_manifest',
        'schema_version': 'v0.1',
        'schema_ref': KERNEL_GUARD_SCHEMA_REF,
        'profile': KERNEL_GUARD_PROFILE,
        'algorithm': KERNEL_GUARD_ALGORITHM,
        'chain_id': str(manifest.get('chain_id') or ''),
        'key_id': key_id,
        'entry_count': len(entries),
        'root_chain_digest': str(manifest.get('root_chain_digest') or ''),
        'manifest_metadata_digest': root_transcript['manifest_metadata_digest'],
        'entry_guards': entry_guards,
        'first_tag': first_tag,
        'last_tag': last_tag,
        'root_tag': root_tag,
    }


def _assert_guard_field(guard: Mapping[str, Any], key: str, expected: Any, *, label: str) -> None:
    actual = guard.get(key)
    if actual != expected:
        raise KernelGuardError(f'{label} {key} mismatch')


def verify_kernel_guard_manifest(
    manifest: Mapping[str, Any],
    guard: Mapping[str, Any],
    *,
    key: str | bytes,
    root: Any = None,
    validate_chain: bool = True,
    validate_schemas: bool = True,
    validate_guard_schema: bool = True,
    strict_jsonschema: bool = False,
    require_lifecycle: bool = False,
) -> Dict[str, Any]:
    """Verify a sidecar HMAC guard against an artifact-chain manifest."""

    if validate_guard_schema:
        try:
            validate_artifact(guard, KERNEL_GUARD_SCHEMA_REF, root=root, strict_jsonschema=strict_jsonschema)
        except Exception as exc:
            raise KernelGuardError(f'kernel guard schema validation failed:{exc}') from exc

    if guard.get('profile') != KERNEL_GUARD_PROFILE:
        raise KernelGuardError('kernel guard profile mismatch')
    if guard.get('algorithm') != KERNEL_GUARD_ALGORITHM:
        raise KernelGuardError('kernel guard algorithm mismatch')
    key_id = str(guard.get('key_id') or '')
    if not key_id:
        raise KernelGuardError('kernel guard missing key_id')

    chain_result: Dict[str, Any] | None = None
    if validate_chain:
        try:
            chain_result = verify_artifact_chain_manifest(
                manifest,
                root=root,
                validate_schemas=validate_schemas,
                strict_jsonschema=strict_jsonschema,
                require_lifecycle=require_lifecycle,
            )
        except ChainVerificationError as exc:
            raise KernelGuardError(str(exc)) from exc

    entries = _entries(manifest)
    entry_guards = guard.get('entry_guards')
    if not isinstance(entry_guards, list) or not all(isinstance(item, Mapping) for item in entry_guards):
        raise KernelGuardError('kernel guard entry_guards is not an array of objects')
    if len(entry_guards) != len(entries):
        raise KernelGuardError('kernel guard entry_count mismatch')
    if int(guard.get('entry_count') or -1) != len(entries):
        raise KernelGuardError('kernel guard entry_count mismatch')
    _assert_guard_field(guard, 'chain_id', str(manifest.get('chain_id') or ''), label='kernel guard root')
    _assert_guard_field(guard, 'root_chain_digest', str(manifest.get('root_chain_digest') or ''), label='kernel guard root')
    _assert_guard_field(guard, 'manifest_metadata_digest', manifest_metadata_digest(manifest), label='kernel guard root')

    previous_tag = ''
    computed_tags = []
    for seq, (entry, entry_guard) in enumerate(zip(entries, entry_guards)):
        nonce = str(entry_guard.get('nonce') or '')
        transcript = _entry_transcript(
            manifest,
            entry,
            seq=seq,
            entry_count=len(entries),
            previous_tag=previous_tag,
            nonce=nonce,
            key_id=key_id,
        )
        for field, expected in transcript.items():
            _assert_guard_field(entry_guard, field, expected, label=f'kernel guard entry[{seq}]')
        expected_tag = _hmac_hex(key, transcript)
        if not hmac.compare_digest(str(entry_guard.get('tag') or ''), expected_tag):
            raise KernelGuardError(f'kernel guard entry[{seq}] tag mismatch')
        computed_tags.append(expected_tag)
        previous_tag = expected_tag

    first_tag = computed_tags[0] if computed_tags else ''
    last_tag = computed_tags[-1] if computed_tags else ''
    _assert_guard_field(guard, 'first_tag', first_tag, label='kernel guard root')
    _assert_guard_field(guard, 'last_tag', last_tag, label='kernel guard root')
    root_transcript = _root_transcript(
        manifest,
        entry_count=len(entries),
        first_tag=first_tag,
        last_tag=last_tag,
        key_id=key_id,
    )
    expected_root_tag = _hmac_hex(key, root_transcript)
    if not hmac.compare_digest(str(guard.get('root_tag') or ''), expected_root_tag):
        raise KernelGuardError('kernel guard root_tag mismatch')

    return {
        'status': 'passed',
        'checked_entries': [str(entry.get('role') or '') for entry in entries],
        'entry_count': len(entries),
        'root_chain_digest': str(manifest.get('root_chain_digest') or ''),
        'guard_profile': KERNEL_GUARD_PROFILE,
        'guard_root_tag': expected_root_tag,
        'key_id': key_id,
        'replay_status': 'not_checked',
        'chain_status': chain_result.get('status') if chain_result else 'not_checked',
    }
