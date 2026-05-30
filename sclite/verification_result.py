from __future__ import annotations

from typing import Any, Dict, Mapping

VERIFICATION_RESULT_SCHEMA_REF = 'schemas/verification_result.v1.schema.json'


def build_guarded_strict_verification_result(
    guard_result: Mapping[str, Any],
    *,
    secure_profile: str,
    security_posture: str,
) -> Dict[str, Any]:
    """Build the stable verifier-result contract for guarded-strict bundles.

    The result is intentionally a local verification receipt. It records
    SCLite layer outcomes and explicit non-claims; it does not add replay
    state, public identity, or runtime enforcement.
    """

    checked_entries = [str(item) for item in guard_result.get('checked_entries') or []]
    return {
        'artifact_type': 'verification_result',
        'schema_version': 'v1',
        'schema_ref': VERIFICATION_RESULT_SCHEMA_REF,
        'profile': secure_profile,
        'security_posture': security_posture,
        'status': 'pass',
        'artifact_chain': 'pass',
        'strict_lifecycle': 'pass',
        'kernel_guard': 'pass',
        'replay': str(guard_result.get('replay_status') or 'not_checked'),
        'public_identity': 'not_claimed',
        'runtime_enforcement': 'not_claimed',
        'entry_count': int(guard_result.get('entry_count') or len(checked_entries)),
        'checked_entries': checked_entries,
        'root_chain_digest': str(guard_result.get('root_chain_digest') or ''),
        'guard_profile': str(guard_result.get('guard_profile') or ''),
        'guard_root_tag': str(guard_result.get('guard_root_tag') or ''),
        'key_id': str(guard_result.get('key_id') or ''),
    }
