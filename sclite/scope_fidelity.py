from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Sequence

from .artifacts import validate_schema_ref
from .hosts import collect_hosts_from_scalars, extract_host
from .json_types import json_array, json_mapping, json_object
from .redaction import sanitize_public_artifact


SCOPE_FIDELITY_ARTIFACT_TYPE = 'scope_fidelity_report'
SCOPE_FIDELITY_SCHEMA_VERSION = 'v0.1'
SCOPE_FIDELITY_SCHEMA_REF = 'schemas/scope_fidelity_report.v0.1.schema.json'


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_str(value: Any) -> str:
    return str(value or '')


def _collect_hosts_from_step(step: Mapping[str, Any]) -> List[str]:
    values: List[Any] = []
    args = step.get('args')
    if isinstance(args, list):
        values.extend(args)
    stdin = _safe_str(step.get('stdin') or '')
    if stdin:
        values.extend(stdin.splitlines())
    return collect_hosts_from_scalars(values)


def summarize_scope_fidelity(*, target: str, normalized_args: Sequence[Any], execution_plan: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    target_host = extract_host(target)
    arg_hosts = collect_hosts_from_scalars(list(normalized_args or []))
    plan_hosts: List[str] = []
    seen_plan: set[str] = set()
    for raw_step in list(execution_plan or []):
        if not isinstance(raw_step, Mapping):
            continue
        for host in _collect_hosts_from_step(raw_step):
            if host not in seen_plan:
                seen_plan.add(host)
                plan_hosts.append(host)
    all_hosts: List[str] = []
    seen_all: set[str] = set()
    for host in [*arg_hosts, *plan_hosts]:
        if host not in seen_all:
            seen_all.add(host)
            all_hosts.append(host)
    mismatched = [host for host in all_hosts if host != target_host] if target_host else list(all_hosts)
    mismatch_sources: List[str] = []
    if target_host:
        if any(host != target_host for host in arg_hosts):
            mismatch_sources.append('normalized_args')
        if any(host != target_host for host in plan_hosts):
            mismatch_sources.append('execution_plan')
    else:
        if arg_hosts:
            mismatch_sources.append('normalized_args')
        if plan_hosts:
            mismatch_sources.append('execution_plan')

    if mismatched:
        verdict = 'fail'
        status = 'cross_host_mismatch'
        match_status = 'mixed'
        reason = f"mismatched_hosts_detected:{','.join(mismatched)}"
    elif all_hosts:
        verdict = 'pass'
        status = 'clean'
        match_status = 'exact'
        reason = 'all_detected_hosts_match_target'
    else:
        verdict = 'review'
        status = 'ambiguous'
        match_status = 'none_detected'
        reason = 'no_hosts_detected_in_execution_shape'

    sources: List[str] = []
    if arg_hosts:
        sources.append('normalized_args')
    if plan_hosts:
        sources.append('execution_plan')
    return {
        'verdict': verdict,
        'target_host': target_host,
        'arg_hosts_detected': arg_hosts,
        'execution_plan_hosts_detected': plan_hosts,
        'all_hosts_detected': all_hosts,
        'mismatched_hosts_detected': mismatched,
        'target_host_match_status': match_status,
        'request_shape_hygiene_status': status,
        'request_shape_hygiene_reason': reason,
        'request_shape_hygiene_source': '+'.join(mismatch_sources or sources) if (mismatch_sources or sources) else 'none',
    }


def build_scope_fidelity_report(
    *,
    target: str,
    normalized_args: Sequence[Any] | None = None,
    execution_plan: Sequence[Mapping[str, Any]] | None = None,
    target_in_scope: bool | None = None,
    source_artifact: str = '',
) -> Dict[str, Any]:
    summary = summarize_scope_fidelity(
        target=target,
        normalized_args=list(normalized_args or []),
        execution_plan=list(execution_plan or []),
    )
    verdict = str(summary['verdict'])
    if target_in_scope is False:
        verdict = 'fail'
        summary['request_shape_hygiene_reason'] = 'target_explicitly_out_of_scope'
    elif target_in_scope is not True and verdict != 'fail':
        verdict = 'review'
        summary['request_shape_hygiene_reason'] = 'target_scope_not_checked'
    report = {
        'artifact_type': SCOPE_FIDELITY_ARTIFACT_TYPE,
        'schema_version': SCOPE_FIDELITY_SCHEMA_VERSION,
        'schema_ref': SCOPE_FIDELITY_SCHEMA_REF,
        'generated_at': _utc_now(),
        'target': _safe_str(target),
        'target_host': summary['target_host'],
        'target_in_scope': target_in_scope,
        'source_artifact': _safe_str(source_artifact),
        'verdict': verdict,
        'request_shape': {
            'arg_hosts_detected': summary['arg_hosts_detected'],
            'execution_plan_hosts_detected': summary['execution_plan_hosts_detected'],
            'all_hosts_detected': summary['all_hosts_detected'],
            'mismatched_hosts_detected': summary['mismatched_hosts_detected'],
            'target_host_match_status': summary['target_host_match_status'],
            'request_shape_hygiene_status': summary['request_shape_hygiene_status'],
            'request_shape_hygiene_reason': summary['request_shape_hygiene_reason'],
            'request_shape_hygiene_source': summary['request_shape_hygiene_source'],
        },
        'public_safety': {
            'live_target_execution': False,
            'protocol_adapter_work': False,
            'public_push': False,
            'static_analysis_only': True,
        },
        'limitations': [
            'static_host_binding_check_only',
            'does_not_resolve_dns_redirects_or_ownership',
            'does_not_prove_legal_authorization',
            'does_not_execute_tools',
        ],
    }
    return json_object(sanitize_public_artifact(report), label='scope_fidelity_report')


def build_scope_fidelity_report_from_approved_spec(approved_spec: Mapping[str, Any], *, source_artifact: str = 'approved_execution_spec') -> Dict[str, Any]:
    scope_facts = json_mapping(approved_spec.get('scope_facts'))
    target = _safe_str(approved_spec.get('target') or scope_facts.get('target') or '')
    normalized_args = json_array(approved_spec.get('normalized_args'))
    execution_plan = json_array(approved_spec.get('execution_plan'))
    target_in_scope = approved_spec.get('target_in_scope')
    if not isinstance(target_in_scope, bool):
        target_in_scope = scope_facts.get('target_in_scope') if isinstance(scope_facts.get('target_in_scope'), bool) else None
    return build_scope_fidelity_report(
        target=target,
        normalized_args=normalized_args,
        execution_plan=execution_plan,
        target_in_scope=target_in_scope,
        source_artifact=source_artifact,
    )


def validate_scope_fidelity_report(report: Mapping[str, Any]) -> None:
    validate_schema_ref(SCOPE_FIDELITY_SCHEMA_REF, report)

LIFECYCLE_SCOPE_FIDELITY_SCHEMA_VERSION = 'v0.2'
LIFECYCLE_SCOPE_FIDELITY_SCHEMA_REF = 'schemas/scope_fidelity_report.v0.2.schema.json'


def _target_entry(role: str, artifact: Mapping[str, Any]) -> Dict[str, Any]:
    target = ''
    host = ''
    source = 'none'
    if role == 'intent_contract':
        raw_target = json_mapping(artifact.get('target'))
        target = _safe_str(raw_target.get('uri') or raw_target.get('host') or '')
        host = extract_host(raw_target.get('host') or raw_target.get('uri') or '')
        source = 'target'
    elif role == 'policy_decision':
        raw_scope = json_mapping(artifact.get('scope'))
        target = _safe_str(raw_scope.get('target') or raw_scope.get('target_host') or '')
        host = extract_host(raw_scope.get('target_host') or raw_scope.get('target') or '')
        source = 'scope'
    elif role == 'execution_contract':
        raw_binding = json_mapping(artifact.get('target_binding'))
        target = _safe_str(raw_binding.get('target') or raw_binding.get('target_host') or '')
        host = extract_host(raw_binding.get('target_host') or raw_binding.get('target') or '')
        source = 'target_binding'
    elif role == 'execution_ticket':
        raw_scope = json_mapping(artifact.get('scope_binding'))
        target = _safe_str(raw_scope.get('target_ref') or raw_scope.get('target_host') or '')
        host = extract_host(raw_scope.get('target_host') or raw_scope.get('target_ref') or '')
        source = 'scope_binding'
    status = 'explicit' if host else 'linked_no_explicit_target'
    return {
        'role': role,
        'artifact_type': _safe_str(artifact.get('artifact_type')),
        'target': target,
        'target_host': host,
        'source': source,
        'status': status,
    }


def _lifecycle_target_in_scope(artifacts_by_role: Mapping[str, Mapping[str, Any]], role: str) -> bool | None:
    artifact = artifacts_by_role.get(role)
    if not isinstance(artifact, Mapping):
        return None
    field = 'scope' if role == 'policy_decision' else 'target_binding'
    value = json_mapping(artifact.get(field)).get('target_in_scope')
    return value if isinstance(value, bool) else None


def build_lifecycle_scope_fidelity_report(
    artifacts_by_role: Mapping[str, Mapping[str, Any]],
    *,
    source_artifact: str = '',
    generated_at: str | None = None,
) -> Dict[str, Any]:
    """Build lifecycle-aware Scope Fidelity v0.2 from local artifacts.

    The v0.2 report compares explicit target hosts across intent, policy,
    execution contract, and scoped ticket artifacts. Receipt and evidence
    artifacts are treated as digest-linked lifecycle artifacts rather than
    independent target authorities unless they expose an explicit target.
    """
    canonical_roles = [
        'intent_contract',
        'policy_decision',
        'execution_contract',
        'execution_ticket',
        'execution_receipt',
        'evidence_contract',
    ]
    entries: List[Dict[str, Any]] = []
    missing_roles: List[str] = []
    for role in canonical_roles:
        artifact = artifacts_by_role.get(role)
        if isinstance(artifact, Mapping):
            entries.append(_target_entry(role, artifact))
        else:
            missing_roles.append(role)
    explicit_hosts = [entry['target_host'] for entry in entries if entry.get('target_host')]
    unique_hosts: List[str] = []
    for host in explicit_hosts:
        if host not in unique_hosts:
            unique_hosts.append(host)
    mismatched = sorted(unique_hosts) if len(unique_hosts) > 1 else []
    if mismatched or missing_roles:
        verdict = 'fail' if mismatched else 'review'
        status = 'cross_role_target_mismatch' if mismatched else 'incomplete_lifecycle'
        reason = f"mismatched lifecycle target hosts: {','.join(mismatched)}" if mismatched else f"missing lifecycle roles: {','.join(missing_roles)}"
    elif unique_hosts:
        verdict = 'pass'
        status = 'consistent'
        reason = 'all explicit lifecycle target hosts match'
    else:
        verdict = 'review'
        status = 'no_explicit_targets'
        reason = 'no explicit target hosts found in lifecycle artifacts'

    # v0.2 has a frozen lifecycle_target_status enum that describes host
    # consistency. Scope assertion is therefore expressed by the verdict and
    # reason, without inventing a schema-incompatible status value.
    scope_assertions = [
        _lifecycle_target_in_scope(artifacts_by_role, 'policy_decision'),
        _lifecycle_target_in_scope(artifacts_by_role, 'execution_contract'),
    ]
    present_scope_assertions = [
        value for role, value in zip(
            ('policy_decision', 'execution_contract'),
            scope_assertions,
        )
        if isinstance(artifacts_by_role.get(role), Mapping)
    ]
    if any(value is False for value in present_scope_assertions):
        verdict = 'fail'
        reason = 'lifecycle target_in_scope is explicitly false'
    elif len(present_scope_assertions) == 2 and any(
        value is not True for value in present_scope_assertions
    ) and verdict != 'fail':
        verdict = 'review'
        reason = 'legacy lifecycle target_in_scope assertion is missing or unknown'
    report = {
        'artifact_type': SCOPE_FIDELITY_ARTIFACT_TYPE,
        'schema_version': LIFECYCLE_SCOPE_FIDELITY_SCHEMA_VERSION,
        'schema_ref': LIFECYCLE_SCOPE_FIDELITY_SCHEMA_REF,
        'generated_at': generated_at or _utc_now(),
        'source_artifact': _safe_str(source_artifact),
        'verdict': verdict,
        'lifecycle_targets': entries,
        'summary': {
            'target_hosts': unique_hosts,
            'mismatched_hosts_detected': mismatched,
            'missing_roles': missing_roles,
            'lifecycle_target_status': status,
            'reason': reason,
        },
        'public_safety': {
            'live_target_execution': False,
            'protocol_adapter_work': False,
            'public_push': False,
            'static_analysis_only': True,
        },
        'limitations': [
            'static_lifecycle_target_review_only',
            'does_not_resolve_dns_redirects_or_ownership',
            'does_not_prove_legal_authorization',
            'does_not_execute_tools',
            'receipt_and_evidence_targets_are_inferred_from_digest_linked_lifecycle_context',
        ],
    }
    return json_object(sanitize_public_artifact(report), label='lifecycle_scope_fidelity_report')


def validate_lifecycle_scope_fidelity_report(report: Mapping[str, Any], *, strict_jsonschema: bool = False) -> None:
    validate_schema_ref(LIFECYCLE_SCOPE_FIDELITY_SCHEMA_REF, report, strict_jsonschema=strict_jsonschema)
