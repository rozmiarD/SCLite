from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from ._json import VerificationLimits, load_json_object
from .errors import SCLiteValidationError
from .kernel_guard import KernelGuardError, _verify_kernel_guard_manifest_with_snapshot
from .tickets import verify_ticket_use_profile
from .verification_result import (
    VerificationResult,
    _verification_result_from_verified_guard,
    build_guarded_strict_verification_result,
)

SECURE_BUNDLE_PROFILE = 'guarded-strict'
SECURE_BUNDLE_POSTURE = 'guarded_domain_auth'
DEFAULT_KERNEL_GUARD_FILENAME = 'kernel_guard_manifest.json'
DEFAULT_ARTIFACT_CHAIN_MANIFEST = 'artifact_chain_manifest.json'


class SecureBundleError(SCLiteValidationError):
    """Raised when the guarded-strict secure bundle profile cannot pass."""

    default_code = 'secure_bundle_failed'


def _load_json_object(
    path: Path,
    *,
    verification_limits: VerificationLimits | None = None,
) -> Dict[str, Any]:
    return load_json_object(path, error_cls=SecureBundleError, limits=verification_limits)


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


def _verify_secure_bundle(
    target: Path | str,
    *,
    guard_path: Path | str | None = None,
    key: str | bytes,
    root: Path | str | None = None,
    validate_schemas: bool = True,
    strict_jsonschema: bool = False,
    max_artifact_bytes: int | None = None,
    max_manifest_entries: int | None = None,
    verification_limits: VerificationLimits | None = None,
    include_local_debug: bool = False,
) -> tuple[Dict[str, Any], VerificationResult]:
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

    manifest = _load_json_object(manifest_path, verification_limits=verification_limits)
    guard = _load_json_object(sidecar_path, verification_limits=verification_limits)
    try:
        result, snapshot = _verify_kernel_guard_manifest_with_snapshot(
            manifest,
            guard,
            key=key,
            root=root_path,
            validate_schemas=validate_schemas,
            strict_jsonschema=strict_jsonschema,
            require_lifecycle=True,
            max_artifact_bytes=max_artifact_bytes,
            max_manifest_entries=max_manifest_entries,
            verification_limits=verification_limits,
        )
    except KernelGuardError as exc:
        raise SecureBundleError(str(exc)) from exc

    if snapshot is None:  # pragma: no cover - guarded secure verification always verifies the chain
        raise SecureBundleError('secure bundle verification did not produce a verified snapshot')
    if result.get('lifecycle_status') != 'passed':
        raise SecureBundleError('strict lifecycle verification did not pass')
    artifacts_by_role = {
        role: artifact.value for role, artifact in snapshot.artifacts_by_role.items()
    }
    ticket_use_result = verify_ticket_use_profile(
        artifacts_by_role,
        strict_jsonschema=strict_jsonschema,
        strict_ticket_profile=True,
        strict_evidence_claims=True,
    )
    if ticket_use_result.get('status') == 'fail' or (
        ticket_use_result.get('status') == 'review'
        and ticket_use_result.get('applicability') == 'verified'
    ):
        raise SecureBundleError('ticket-use verification failed:' + str(ticket_use_result.get('detail') or 'unknown'))

    verification_result = _verification_result_from_verified_guard(
        result,
        secure_profile=SECURE_BUNDLE_PROFILE,
        security_posture=SECURE_BUNDLE_POSTURE,
        ticket_use_result=ticket_use_result,
    )
    serialized_result = build_guarded_strict_verification_result(
        result,
        secure_profile=SECURE_BUNDLE_PROFILE,
        security_posture=SECURE_BUNDLE_POSTURE,
        ticket_use_result=ticket_use_result,
    )
    response = {
        **result,
        'secure_profile': SECURE_BUNDLE_PROFILE,
        'security_posture': SECURE_BUNDLE_POSTURE,
        'ticket_use_status': ticket_use_result.get('status') or 'review',
        'ticket_use_applicability': ticket_use_result.get('applicability') or '',
        'ticket_use_detail': ticket_use_result.get('detail') or '',
        'manifest_path': str(manifest_path.relative_to(root_path)),
        'guard_path': str(sidecar_path.relative_to(root_path)),
        'chain_id': str(manifest.get('chain_id') or ''),
        'ticket_id': str(artifacts_by_role.get('execution_ticket', {}).get('ticket_id') or ''),
        'fail_closed': True,
        'replay_status': result.get('replay_status') or 'not_checked',
        'scope_authority_authenticated': (
            'authenticated_channel'
            if result.get('scope_status') == 'authority_artifact_bound'
            else 'not_checked'
        ),
        'verification_result': serialized_result,
    }
    if include_local_debug:
        response['local_debug'] = {
            'manifest_path': str(manifest_path),
            'guard_path': str(sidecar_path),
            'root_path': str(root_path),
        }
    return response, verification_result


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
    verification_limits: VerificationLimits | None = None,
    include_local_debug: bool = False,
) -> Dict[str, Any]:
    """Compatibility dictionary API for guarded-strict verification."""

    response, _result = _verify_secure_bundle(
        target,
        guard_path=guard_path,
        key=key,
        root=root,
        validate_schemas=validate_schemas,
        strict_jsonschema=strict_jsonschema,
        max_artifact_bytes=max_artifact_bytes,
        max_manifest_entries=max_manifest_entries,
        verification_limits=verification_limits,
        include_local_debug=include_local_debug,
    )
    return response


def verify_secure_bundle_result(
    target: Path | str,
    *,
    guard_path: Path | str | None = None,
    key: str | bytes,
    root: Path | str | None = None,
    validate_schemas: bool = True,
    strict_jsonschema: bool = False,
    max_artifact_bytes: int | None = None,
    max_manifest_entries: int | None = None,
    verification_limits: VerificationLimits | None = None,
) -> VerificationResult:
    """Verify a guarded-strict bundle and return the typed production result."""

    _response, result = _verify_secure_bundle(
        target,
        guard_path=guard_path,
        key=key,
        root=root,
        validate_schemas=validate_schemas,
        strict_jsonschema=strict_jsonschema,
        max_artifact_bytes=max_artifact_bytes,
        max_manifest_entries=max_manifest_entries,
        verification_limits=verification_limits,
    )
    return result
