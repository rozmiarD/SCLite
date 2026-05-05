from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Sequence

from .artifacts import validate_schema_ref
from .hosts import collect_hosts_from_scalars, extract_host
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
    report = {
        'artifact_type': SCOPE_FIDELITY_ARTIFACT_TYPE,
        'schema_version': SCOPE_FIDELITY_SCHEMA_VERSION,
        'schema_ref': SCOPE_FIDELITY_SCHEMA_REF,
        'generated_at': _utc_now(),
        'target': _safe_str(target),
        'target_host': summary['target_host'],
        'target_in_scope': target_in_scope,
        'source_artifact': _safe_str(source_artifact),
        'verdict': summary['verdict'],
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
    return sanitize_public_artifact(report)


def build_scope_fidelity_report_from_approved_spec(approved_spec: Mapping[str, Any], *, source_artifact: str = 'approved_execution_spec') -> Dict[str, Any]:
    target = _safe_str(approved_spec.get('target') or ((approved_spec.get('scope_facts') or {}) if isinstance(approved_spec.get('scope_facts'), dict) else {}).get('target') or '')
    normalized_args = approved_spec.get('normalized_args') if isinstance(approved_spec.get('normalized_args'), list) else []
    execution_plan = approved_spec.get('execution_plan') if isinstance(approved_spec.get('execution_plan'), list) else []
    target_in_scope = approved_spec.get('target_in_scope')
    if not isinstance(target_in_scope, bool):
        scope_facts = approved_spec.get('scope_facts') if isinstance(approved_spec.get('scope_facts'), dict) else {}
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
