from __future__ import annotations

from pathlib import Path, PureWindowsPath
from typing import Any, Dict, Literal, Mapping, Sequence

from .errors import SCLiteValidationError

DisclosureStatus = Literal[
    'unknown',
    'operator_asserted',
    'checks_performed',
    'externally_verified',
]
DisclosureCoverage = Literal['not_checked', 'heuristic_checked', 'externally_verified']

DISCLOSURE_STATUS_ORDER: tuple[DisclosureStatus, ...] = (
    'unknown',
    'operator_asserted',
    'checks_performed',
    'externally_verified',
)


class DisclosureStatusError(SCLiteValidationError):
    default_code = 'disclosure_status_failed'


def validate_disclosure_transition(
    current: DisclosureStatus,
    proposed: DisclosureStatus,
) -> None:
    """Reject a disclosure-status downgrade."""

    if current not in DISCLOSURE_STATUS_ORDER or proposed not in DISCLOSURE_STATUS_ORDER:
        raise DisclosureStatusError('unsupported disclosure status')
    if DISCLOSURE_STATUS_ORDER.index(proposed) < DISCLOSURE_STATUS_ORDER.index(current):
        raise DisclosureStatusError(f'disclosure status downgrade: {current} -> {proposed}')


def build_disclosure_status(
    *,
    status: DisclosureStatus = 'unknown',
    checks: Sequence[str] = (),
    policy: str = '',
    coverage: Mapping[str, DisclosureCoverage] | None = None,
) -> Dict[str, Any]:
    """Build a truthful disclosure status without authorizing publication."""

    if status not in DISCLOSURE_STATUS_ORDER:
        raise DisclosureStatusError(f'unsupported disclosure status: {status}')
    normalized_checks = [str(item) for item in checks if str(item)]
    if status in {'checks_performed', 'externally_verified'} and not normalized_checks:
        raise DisclosureStatusError(f'{status} requires concrete checks')
    if status in {'checks_performed', 'externally_verified'} and not policy:
        raise DisclosureStatusError(f'{status} requires a policy')
    normalized_coverage = {
        'credentials': 'not_checked',
        'private_paths': 'not_checked',
        'raw_output': 'not_checked',
        **dict(coverage or {}),
    }
    if any(value not in {'not_checked', 'heuristic_checked', 'externally_verified'} for value in normalized_coverage.values()):
        raise DisclosureStatusError('unsupported disclosure coverage')
    return {
        'status': status,
        'checks': normalized_checks,
        'policy': policy,
        'coverage': normalized_coverage,
        'publication_authorized': False,
    }


def legacy_public_safe(status: DisclosureStatus) -> bool:
    """Derive the deprecated boolean without promoting unknown/asserted input."""

    return status == 'externally_verified'


def relative_public_path(value: str | Path) -> str:
    """Return a normalized relative label without workstation topology."""

    text = str(value).replace('\\', '/')
    windows = PureWindowsPath(str(value))
    path = Path(text)
    if path.is_absolute() or windows.is_absolute() or '..' in path.parts:
        return windows.name or path.name or 'artifact.json'
    normalized = path.as_posix()
    return normalized.lstrip('./') or path.name or 'artifact.json'
