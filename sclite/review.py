from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping

from ._json import VerificationLimits, load_json_object
from .artifacts import JsonSchemaValidationError, validate_artifact
from .integrity import ChainVerificationError
from .integrity.chain import _verify_artifact_chain_manifest_with_snapshot
from .json_types import json_array
from .scope_fidelity import build_lifecycle_scope_fidelity_report, validate_lifecycle_scope_fidelity_report
from .tickets import verify_ticket_use_profile

REVIEW_RECORD_SCHEMA = 'review_record.v0.1'
REVIEW_RECORD_SCHEMA_REF = 'schemas/review_record.v0.1.schema.json'


class ReviewRecordError(ValueError):
    """Raised when a lifecycle review cannot be produced cleanly."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json_object(
    path: Path,
    *,
    verification_limits: VerificationLimits | None = None,
) -> Dict[str, Any]:
    return load_json_object(path, error_cls=ReviewRecordError, limits=verification_limits)


def _schema_ref(value: Mapping[str, Any]) -> str:
    return str(value.get('schema_ref') or value.get('schema') or '')


def _status_to_verdict(statuses: List[str]) -> str:
    if 'fail' in statuses:
        return 'fail'
    if 'review' in statuses:
        return 'review'
    return 'pass'


def _check(name: str, status: str, detail: str = '', count: int | None = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {'name': name, 'status': status, 'detail': detail}
    if count is not None:
        result['count'] = count
    return result


def _assert_manifest_paths_within_root(manifest: Mapping[str, Any], root: Path) -> None:
    """Reject escaped paths before the snapshot loader opens any payload."""

    entries = manifest.get('entries')
    if not isinstance(entries, list):
        return
    base = root.resolve()
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            continue
        rel_path = str(entry.get('path') or '')
        if not rel_path:
            continue
        artifact_path = (base / rel_path).resolve()
        try:
            artifact_path.relative_to(base)
        except ValueError as exc:
            raise ReviewRecordError(
                f'manifest entry[{index}] path escapes root: {rel_path}'
            ) from exc


def build_review_record_from_manifest(
    manifest_path: Path | str,
    *,
    root: Path | str | None = None,
    strict_jsonschema: bool = False,
    generated_at: str | None = None,
    verification_limits: VerificationLimits | None = None,
) -> Dict[str, Any]:
    """Build a public-safe lifecycle review record for a local SCLite bundle.

    The review record aggregates local/static validation only: schema checks,
    chain integrity, lifecycle binding checks, and lifecycle-aware Scope
    Fidelity. It does not execute tools, make authorization decisions, verify
    signer identity, or prove carrier delivery.
    """
    manifest_path = Path(manifest_path).resolve()
    base = Path(root).resolve() if root else manifest_path.parent
    manifest = _load_json_object(manifest_path, verification_limits=verification_limits)
    _assert_manifest_paths_within_root(manifest, base)
    checks: List[Dict[str, Any]] = []
    statuses: List[str] = []
    record_generated_at = generated_at or _utc_now()

    artifacts_by_role: Dict[str, Mapping[str, Any]] = {}
    chain_result: Dict[str, Any] | None = None
    try:
        chain_result, snapshot = _verify_artifact_chain_manifest_with_snapshot(
            manifest,
            root=base,
            validate_schemas=True,
            strict_jsonschema=strict_jsonschema,
            require_lifecycle=True,
            verification_limits=verification_limits,
        )
        artifacts_by_role = {
            role: artifact.value for role, artifact in snapshot.artifacts_by_role.items()
        }
        checks.append(_check(
            'schema_validation',
            'pass',
            'all manifest artifacts validated against declared schemas',
            len(artifacts_by_role),
        ))
        statuses.append('pass')
        semantic_checks = json_array(chain_result.get('semantic_checks'))
        checks.append(_check('chain_integrity', 'pass', str(chain_result.get('root_chain_digest') or ''), int(chain_result.get('entry_count') or 0)))
        lifecycle_status = str(chain_result.get('lifecycle_status') or 'review')
        lifecycle_check_status = 'pass' if lifecycle_status == 'passed' else 'review'
        if lifecycle_check_status == 'pass':
            lifecycle_detail = 'semantic checks present and strict lifecycle passed'
        elif chain_result.get('scope_status') != 'operator_asserted':
            lifecycle_detail = str(chain_result.get('scope_detail') or 'strict lifecycle scope was not verified')
        else:
            lifecycle_detail = str(chain_result.get('ticket_validity_detail') or 'strict lifecycle ticket validity was not verified')
        checks.append(_check(
            'lifecycle_binding',
            lifecycle_check_status,
            lifecycle_detail,
            len(semantic_checks),
        ))
        statuses.extend(['pass', lifecycle_check_status])
    except (ChainVerificationError, JsonSchemaValidationError) as exc:
        checks.append(_check('schema_validation', 'fail', str(exc)))
        checks.append(_check('chain_integrity', 'fail', str(exc)))
        checks.append(_check('lifecycle_binding', 'fail', str(exc)))
        statuses.extend(['fail', 'fail', 'fail'])

    try:
        source_artifact = str(manifest_path.relative_to(base))
    except ValueError:
        source_artifact = manifest_path.name
    scope_report = build_lifecycle_scope_fidelity_report(
        artifacts_by_role,
        source_artifact=source_artifact,
        generated_at=record_generated_at,
    )
    validate_lifecycle_scope_fidelity_report(scope_report, strict_jsonschema=strict_jsonschema)
    checks.append(_check('scope_fidelity', str(scope_report['verdict']), str(scope_report['summary']['reason']), len(scope_report.get('lifecycle_targets') or [])))
    statuses.append(str(scope_report['verdict']))

    ticket_use_result = verify_ticket_use_profile(
        artifacts_by_role,
        strict_jsonschema=strict_jsonschema,
    )
    ticket_use_status = str(ticket_use_result.get('status') or 'review')
    ticket_use_checks = json_array(ticket_use_result.get('checks'))
    checks.append(_check(
        'ticket_use_profile',
        ticket_use_status,
        str(ticket_use_result.get('detail') or ''),
        len(ticket_use_checks),
    ))
    statuses.append(ticket_use_status)

    verdict = _status_to_verdict(statuses)
    target_hosts = sorted({str(item.get('target_host')) for item in scope_report.get('lifecycle_targets', []) if isinstance(item, Mapping) and item.get('target_host')})
    record = {
        'artifact_type': 'review_record',
        'schema_version': 'v0.1',
        'schema_ref': REVIEW_RECORD_SCHEMA_REF,
        'generated_at': record_generated_at,
        'review_id': 'review-record-' + (str(chain_result.get('root_chain_digest'))[:12] if chain_result else 'unverified'),
        'review_profile': 'sclite-lifecycle-review-v0.1',
        'source_manifest': str(manifest_path),
        'verdict': verdict,
        'summary': {
            'artifact_count': len(artifacts_by_role),
            'target_hosts': target_hosts,
            'root_chain_digest': chain_result.get('root_chain_digest') if chain_result else '',
            'scope_fidelity_verdict': scope_report['verdict'],
            'ticket_use_status': ticket_use_status,
            'ticket_use_applicability': ticket_use_result.get('applicability') or '',
            'ticket_id': ticket_use_result.get('ticket_id') or '',
            'receipt_id': ticket_use_result.get('receipt_id') or '',
        },
        'checks': checks,
        'scope_fidelity_report': scope_report,
        'public_safety': {
            'live_target_execution': False,
            'protocol_adapter_work': False,
            'trust_authority_decision': False,
            'public_push': False,
            'static_analysis_only': True,
        },
        'non_claims': [
            'does_not_execute_tools',
            'does_not_prove_legal_authorization',
            'does_not_prove_signer_identity',
            'does_not_prove_carrier_delivery',
            'does_not_replace_runtime_policy_decision',
        ],
    }
    validate_artifact(record, REVIEW_RECORD_SCHEMA, strict_jsonschema=strict_jsonschema)
    return record


def review_record_markdown(record: Mapping[str, Any]) -> str:
    lines = [
        '# SCLite Review Record',
        '',
        f"verdict: `{record.get('verdict')}`",
        f"review_profile: `{record.get('review_profile')}`",
        f"source_manifest: `{record.get('source_manifest')}`",
        '',
        '## Checks',
    ]
    for check in record.get('checks', []) if isinstance(record.get('checks'), list) else []:
        if isinstance(check, Mapping):
            lines.append(f"- `{check.get('status')}` — {check.get('name')}: {check.get('detail')}")
    lines.extend([
        '',
        '## Non-claims',
    ])
    for item in record.get('non_claims', []) if isinstance(record.get('non_claims'), list) else []:
        lines.append(f'- {item}')
    return '\n'.join(lines) + '\n'
