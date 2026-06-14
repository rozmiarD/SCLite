from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping

from ._json import load_json_object
from .kernel_guard import KernelGuardError, verify_kernel_guard_manifest
from .tickets import verify_ticket_use_profile
from .verification_result import build_guarded_strict_verification_result

SECURE_BUNDLE_PROFILE = 'guarded-strict'
SECURE_BUNDLE_POSTURE = 'guarded_domain_auth'
DEFAULT_KERNEL_GUARD_FILENAME = 'kernel_guard_manifest.json'
DEFAULT_ARTIFACT_CHAIN_MANIFEST = 'artifact_chain_manifest.json'


class SecureBundleError(ValueError):
    """Raised when the guarded-strict secure bundle profile cannot pass."""


def _load_json_object(path: Path) -> Dict[str, Any]:
    return load_json_object(path, error_cls=SecureBundleError)


def resolve_manifest_path(target: Path | str) -> Path:
    """Resolve a secure-bundle target to an artifact-chain manifest path."""

    path = Path(target)
    if path.is_dir():
        return path / DEFAULT_ARTIFACT_CHAIN_MANIFEST
    return path


def resolve_guard_path(manifest_path: Path | str, guard_path: Path | str | None = None) -> Path:
    """Resolve an explicit or default Kernel Guard sidecar path."""

    if guard_path:
        return Path(guard_path)
    return Path(manifest_path).parent / DEFAULT_KERNEL_GUARD_FILENAME


def _assert_under_root(path: Path, root: Path, *, label: str) -> None:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise SecureBundleError(f'{label} path escapes root: {path}') from exc


def _artifacts_from_manifest(
    manifest: Mapping[str, Any],
    root: Path,
    *,
    max_artifact_bytes: int | None = None,
) -> Dict[str, Mapping[str, Any]]:
    entries = manifest.get('entries')
    if not isinstance(entries, list):
        raise SecureBundleError('manifest.entries is not an array')
    artifacts: Dict[str, Mapping[str, Any]] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            raise SecureBundleError(f'manifest entry[{index}] is not an object')
        role = str(entry.get('role') or '')
        rel_path = str(entry.get('path') or '')
        if not role or not rel_path:
            continue
        artifact_path = (root / rel_path).resolve()
        _assert_under_root(artifact_path, root, label=f'artifact {role}')
        artifacts[role] = load_json_object(artifact_path, error_cls=SecureBundleError, max_bytes=max_artifact_bytes)
    return artifacts


def verify_secure_bundle(
    target: Path | str,
    *,
    guard_path: Path | str | None = None,
    key: str | bytes,
    root: Path | str | None = None,
    validate_schemas: bool = True,
    strict_jsonschema: bool = False,
    max_artifact_bytes: int | None = None,
    max_manifest_entries: int | None = None,
) -> Dict[str, Any]:
    """Verify the guarded-strict secure bundle profile.

    This profile is fail-closed by design: it always requires the canonical
    lifecycle role sequence, artifact-chain verification, and a
    kernel_guard_hmac_v1 sidecar. Replay freshness remains outside SCLite and
    is reported as not checked.
    """

    manifest_path = resolve_manifest_path(target).resolve()
    sidecar_path = resolve_guard_path(manifest_path, guard_path).resolve()
    root_path = Path(root).resolve() if root else manifest_path.parent
    _assert_under_root(manifest_path, root_path, label='manifest')
    _assert_under_root(sidecar_path, root_path, label='guard')
    if not manifest_path.is_file():
        raise SecureBundleError(f'missing artifact-chain manifest: {manifest_path}')
    if not sidecar_path.is_file():
        raise SecureBundleError(f'missing kernel guard sidecar: {sidecar_path}')

    manifest = _load_json_object(manifest_path)
    guard = _load_json_object(sidecar_path)
    try:
        result = verify_kernel_guard_manifest(
            manifest,
            guard,
            key=key,
            root=root_path,
            validate_schemas=validate_schemas,
            strict_jsonschema=strict_jsonschema,
            require_lifecycle=True,
            max_artifact_bytes=max_artifact_bytes,
            max_manifest_entries=max_manifest_entries,
        )
    except KernelGuardError as exc:
        raise SecureBundleError(str(exc)) from exc

    artifacts_by_role = _artifacts_from_manifest(manifest, root_path, max_artifact_bytes=max_artifact_bytes)
    ticket_use_result = verify_ticket_use_profile(
        artifacts_by_role,
        strict_jsonschema=strict_jsonschema,
        strict_ticket_profile=True,
        strict_evidence_claims=True,
    )
    if ticket_use_result.get('status') == 'fail':
        raise SecureBundleError('ticket-use verification failed:' + str(ticket_use_result.get('detail') or 'unknown'))

    verification_result = build_guarded_strict_verification_result(
        result,
        secure_profile=SECURE_BUNDLE_PROFILE,
        security_posture=SECURE_BUNDLE_POSTURE,
        ticket_use_result=ticket_use_result,
    )
    return {
        **result,
        'secure_profile': SECURE_BUNDLE_PROFILE,
        'security_posture': SECURE_BUNDLE_POSTURE,
        'ticket_use_status': ticket_use_result.get('status') or 'review',
        'ticket_use_applicability': ticket_use_result.get('applicability') or '',
        'ticket_use_detail': ticket_use_result.get('detail') or '',
        'manifest_path': str(manifest_path),
        'guard_path': str(sidecar_path),
        'fail_closed': True,
        'replay_status': result.get('replay_status') or 'not_checked',
        'verification_result': verification_result,
    }
