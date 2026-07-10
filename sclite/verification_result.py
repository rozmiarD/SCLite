from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal, Mapping

from ._version import SCLITE_VERSION

VERIFICATION_RESULT_SCHEMA_REF = 'schemas/verification_result.v1.schema.json'
VERIFICATION_RESULT_SCHEMA_REF_V1_1 = 'schemas/verification_result.v1.1.schema.json'
VerificationLayerStatus = Literal['pass', 'fail', 'review', 'not_checked', 'not_applicable']


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """Typed, self-described outcome produced by a SCLite verifier.

    The type reduces accidental misuse; it is not an authentication token and
    does not provide in-process unforgeability. Hosts must re-verify source
    material or authenticate the result over a trusted channel.
    """

    profile: str
    security_posture: str
    status: Literal['pass', 'fail']
    artifact_chain: VerificationLayerStatus
    strict_lifecycle: VerificationLayerStatus
    kernel_guard: VerificationLayerStatus
    ticket_use: VerificationLayerStatus
    ticket_use_applicability: str
    replay: VerificationLayerStatus
    entry_count: int
    checked_entries: tuple[str, ...]
    bundle_digest: str
    guard_profile: str
    guard_root_tag: str
    key_id: str
    policy: str
    verifier_version: str
    checks: tuple[str, ...]
    public_identity: Literal['not_claimed'] = 'not_claimed'
    runtime_enforcement: Literal['not_claimed'] = 'not_claimed'


def serialize_verification_result(result: VerificationResult) -> Dict[str, Any]:
    """Serialize a typed result to the public v1.1 JSON contract."""

    return {
        'artifact_type': 'verification_result',
        'schema_version': 'v1.1',
        'schema_ref': VERIFICATION_RESULT_SCHEMA_REF_V1_1,
        'profile': result.profile,
        'security_posture': result.security_posture,
        'status': result.status,
        'artifact_chain': result.artifact_chain,
        'strict_lifecycle': result.strict_lifecycle,
        'kernel_guard': result.kernel_guard,
        'ticket_use': result.ticket_use,
        'ticket_use_applicability': result.ticket_use_applicability,
        'replay': result.replay,
        'public_identity': result.public_identity,
        'runtime_enforcement': result.runtime_enforcement,
        'entry_count': result.entry_count,
        'checked_entries': list(result.checked_entries),
        'bundle_digest': result.bundle_digest,
        'guard_profile': result.guard_profile,
        'guard_root_tag': result.guard_root_tag,
        'key_id': result.key_id,
        'policy': result.policy,
        'verifier_version': result.verifier_version,
        'checks': list(result.checks),
    }


def _verification_result_from_verified_guard(
    guard_result: Mapping[str, Any],
    *,
    secure_profile: str,
    security_posture: str,
    ticket_use_result: Mapping[str, Any],
) -> VerificationResult:
    """Construct a result only after the production verifier completed."""

    checked_entries = tuple(str(item) for item in guard_result.get('checked_entries') or [])
    return VerificationResult(
        profile=secure_profile,
        security_posture=security_posture,
        status='pass',
        artifact_chain='pass',
        strict_lifecycle='pass',
        kernel_guard='pass',
        ticket_use=str(ticket_use_result.get('status') or 'review'),  # type: ignore[arg-type]
        ticket_use_applicability=str(ticket_use_result.get('applicability') or ''),
        replay=str(guard_result.get('replay_status') or 'not_checked'),  # type: ignore[arg-type]
        entry_count=int(guard_result.get('entry_count') or len(checked_entries)),
        checked_entries=checked_entries,
        bundle_digest=str(guard_result.get('root_chain_digest') or ''),
        guard_profile=str(guard_result.get('guard_profile') or ''),
        guard_root_tag=str(guard_result.get('guard_root_tag') or ''),
        key_id=str(guard_result.get('key_id') or ''),
        policy=secure_profile,
        verifier_version=SCLITE_VERSION,
        checks=(
            'artifact_chain',
            'strict_lifecycle',
            'kernel_guard_hmac',
            'manifest_metadata_binding',
            'ticket_use_profile',
        ),
    )


def build_guarded_strict_verification_result(
    guard_result: Mapping[str, Any],
    *,
    secure_profile: str,
    security_posture: str,
    ticket_use_result: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Compatibility fixture builder retained through SCLite 2.0.

    This function performs no verification. New fixtures should import
    ``build_guarded_strict_verification_result_fixture`` from ``sclite.testing``.
    Production callers should use ``verify_secure_bundle_result``.
    """

    from .testing import build_guarded_strict_verification_result_fixture

    return build_guarded_strict_verification_result_fixture(
        guard_result,
        secure_profile=secure_profile,
        security_posture=security_posture,
        ticket_use_result=ticket_use_result,
    )
