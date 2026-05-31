from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from ._json import load_json_object
from .kernel_guard import KernelGuardError, verify_kernel_guard_manifest
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


def verify_secure_bundle(
    target: Path | str,
    *,
    guard_path: Path | str | None = None,
    key: str | bytes,
    root: Path | str | None = None,
    validate_schemas: bool = True,
    strict_jsonschema: bool = False,
) -> Dict[str, Any]:
    """Verify the guarded-strict secure bundle profile.

    This profile is fail-closed by design: it always requires the canonical
    lifecycle role sequence, artifact-chain verification, and a
    kernel_guard_hmac_v1 sidecar. Replay freshness remains outside SCLite and
    is reported as not checked.
    """

    manifest_path = resolve_manifest_path(target).resolve()
    sidecar_path = resolve_guard_path(manifest_path, guard_path).resolve()
    if not manifest_path.is_file():
        raise SecureBundleError(f'missing artifact-chain manifest: {manifest_path}')
    if not sidecar_path.is_file():
        raise SecureBundleError(f'missing kernel guard sidecar: {sidecar_path}')

    manifest = _load_json_object(manifest_path)
    guard = _load_json_object(sidecar_path)
    root_path = Path(root).resolve() if root else manifest_path.parent
    try:
        result = verify_kernel_guard_manifest(
            manifest,
            guard,
            key=key,
            root=root_path,
            validate_schemas=validate_schemas,
            strict_jsonschema=strict_jsonschema,
            require_lifecycle=True,
        )
    except KernelGuardError as exc:
        raise SecureBundleError(str(exc)) from exc

    verification_result = build_guarded_strict_verification_result(
        result,
        secure_profile=SECURE_BUNDLE_PROFILE,
        security_posture=SECURE_BUNDLE_POSTURE,
    )
    return {
        **result,
        'secure_profile': SECURE_BUNDLE_PROFILE,
        'security_posture': SECURE_BUNDLE_POSTURE,
        'manifest_path': str(manifest_path),
        'guard_path': str(sidecar_path),
        'fail_closed': True,
        'replay_status': result.get('replay_status') or 'not_checked',
        'verification_result': verification_result,
    }
