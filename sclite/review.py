from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping

from ._json import load_json_object
from .artifacts import JsonSchemaValidationError, validate_artifact
from .integrity import ChainVerificationError, verify_artifact_chain_manifest
from .scope_fidelity import build_lifecycle_scope_fidelity_report, validate_lifecycle_scope_fidelity_report

REVIEW_RECORD_SCHEMA = 'review_record.v0.1'
REVIEW_RECORD_SCHEMA_REF = 'schemas/review_record.v0.1.schema.json'


class ReviewRecordError(ValueError):
    """Raised when a lifecycle review cannot be produced cleanly."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json_object(path: Path) -> Dict[str, Any]:
    return load_json_object(path, error_cls=ReviewRecordError)


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


def _artifact_paths_from_manifest(manifest: Mapping[str, Any], root: Path) -> Dict[str, Path]:
    entries = manifest.get('entries')
    if not isinstance(entries, list):
        raise ReviewRecordError('manifest.entries is not an array')
    base = root.resolve()
    result: Dict[str, Path] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        role = str(entry.get('role') or '')
        rel_path = str(entry.get('path') or '')
        if role and rel_path:
            artifact_path = (base / rel_path).resolve()
            try:
                artifact_path.relative_to(base)
            except ValueError as exc:
                raise ReviewRecordError(f'manifest entry path escapes root: {rel_path}') from exc
            result[role] = artifact_path
    return result


def build_review_record_from_manifest(
    manifest_path: Path | str,
    *,
    root: Path | str | None = None,
    strict_jsonschema: bool = False,
    generated_at: str | None = None,
) -> Dict[str, Any]:
    """Build a public-safe lifecycle review record for a local SCLite bundle.

    The review record aggregates local/static validation only: schema checks,
    chain integrity, lifecycle binding checks, and lifecycle-aware Scope
    Fidelity. It does not execute tools, make authorization decisions, verify
    signer identity, or prove carrier delivery.
    """
    manifest_path = Path(manifest_path).resolve()
    base = Path(root).resolve() if root else manifest_path.parent
    manifest = _load_json_object(manifest_path)
    checks: List[Dict[str, Any]] = []
    statuses: List[str] = []
    record_generated_at = generated_at or _utc_now()

    artifact_paths = _artifact_paths_from_manifest(manifest, base)
    artifacts_by_role: Dict[str, Mapping[str, Any]] = {}
    schema_errors: List[str] = []
    for role, path in artifact_paths.items():
        try:
            value = _load_json_object(path)
            artifacts_by_role[role] = value
            schema_ref = _schema_ref(value)
            if schema_ref:
                validate_artifact(value, schema_ref, root=base, strict_jsonschema=strict_jsonschema)
        except (OSError, ValueError, JsonSchemaValidationError) as exc:
            schema_errors.append(f'{role}:{exc}')
    if schema_errors:
        checks.append(_check('schema_validation', 'fail', '; '.join(schema_errors), len(schema_errors)))
        statuses.append('fail')
    else:
        checks.append(_check('schema_validation', 'pass', 'all manifest artifacts validated against declared schemas', len(artifact_paths)))
        statuses.append('pass')

    chain_result: Dict[str, Any] | None = None
    try:
        chain_result = verify_artifact_chain_manifest(
            manifest,
            root=base,
            validate_schemas=True,
            strict_jsonschema=strict_jsonschema,
            require_lifecycle=True,
        )
        semantic_checks = chain_result.get('semantic_checks') if isinstance(chain_result.get('semantic_checks'), list) else []
        checks.append(_check('chain_integrity', 'pass', str(chain_result.get('root_chain_digest') or ''), int(chain_result.get('entry_count') or 0)))
        checks.append(_check('lifecycle_binding', 'pass' if semantic_checks else 'review', 'semantic checks present' if semantic_checks else 'manifest did not expose canonical lifecycle semantic checks', len(semantic_checks)))
        statuses.extend(['pass', 'pass' if semantic_checks else 'review'])
    except (ChainVerificationError, JsonSchemaValidationError) as exc:
        checks.append(_check('chain_integrity', 'fail', str(exc)))
        checks.append(_check('lifecycle_binding', 'fail', str(exc)))
        statuses.extend(['fail', 'fail'])

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

    ticket_use_status = 'review'
    ticket = artifacts_by_role.get('execution_ticket')
    if isinstance(ticket, Mapping) and ticket.get('schema_version') == 'v0.3':
        ticket_use_status = 'pass'
        detail = 'v0.3 ticket-use semantics available for downstream verification'
    else:
        detail = 'ticket-use verification requires scoped execution_ticket.v0.3 artifacts'
    checks.append(_check('ticket_use_profile', ticket_use_status, detail))
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
            'artifact_count': len(artifact_paths),
            'target_hosts': target_hosts,
            'root_chain_digest': chain_result.get('root_chain_digest') if chain_result else '',
            'scope_fidelity_verdict': scope_report['verdict'],
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
