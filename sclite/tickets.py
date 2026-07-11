from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Mapping, Sequence

from .artifacts import JsonSchemaValidationError, validate_artifact
from .errors import SCLiteValidationError
from .integrity import artifact_descriptor
from .json_types import json_array, json_mapping

SCOPED_TICKET_SCHEMA_REF = 'schemas/execution_ticket.v0.3.schema.json'
TICKET_PROFILES = {'review_record', 'scoped_execution_ticket', 'external_capability_ref'}
CONSUMABLE_APPROVAL_STATUSES = {'approved_for_dry_run', 'approved'}
BLOCKED_RECEIPT_STATUSES = {'blocked', 'rejected', 'denied', 'failed', 'skipped', 'not_executed'}
COMPLETED_RECEIPT_STATUSES = {'completed', 'succeeded'}
DRY_RUN_RECEIPT_STATUSES = {'dry_run', 'skipped', 'not_executed'}
EXECUTION_CLAIM_MARKERS = {
    'actual_execution',
    'command_executed',
    'completed_execution',
    'execution_performed',
    'executed_command',
    'tool_executed',
}
NETWORK_CLAIM_MARKERS = {'live_network', 'network_execution', 'network_observed'}


class TicketSemanticError(SCLiteValidationError):
    """Raised when an ExecutionTicket is well-shaped but semantically unsafe."""

    default_code = 'ticket_semantics_failed'


class TicketUseVerificationError(SCLiteValidationError):
    """Raised when a receipt/evidence bundle exceeds a scoped ticket."""

    default_code = 'ticket_use_verification_failed'


def normalized_args_digest(normalized_args: Sequence[Any]) -> str:
    """Return the scoped-ticket digest for normalized execution arguments."""
    encoded = json.dumps(list(normalized_args), sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')
    return 'sha256:' + hashlib.sha256(encoded).hexdigest()


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TicketSemanticError(f'{label} must be an object')
    return value


def _ticket_schema_ref(ticket: Mapping[str, Any]) -> str:
    return str(ticket.get('schema_ref') or SCOPED_TICKET_SCHEMA_REF)


def validate_ticket_schema(ticket: Mapping[str, Any], *, strict_jsonschema: bool = False) -> None:
    """Validate an ExecutionTicket artifact against its declared schema."""
    try:
        validate_artifact(dict(ticket), _ticket_schema_ref(ticket), strict_jsonschema=strict_jsonschema)
    except JsonSchemaValidationError:
        raise


def _mode_level(mode: str) -> int:
    return {'dry_run': 0, 'live': 1}.get(str(mode), 99)


def _linked_execution_contract_descriptor(ticket: Mapping[str, Any]) -> Mapping[str, Any]:
    links = _require_mapping(ticket.get('links'), 'ticket.links')
    execution_contract = _require_mapping(links.get('execution_contract'), 'ticket.links.execution_contract')
    return _require_mapping(execution_contract.get('descriptor'), 'ticket.links.execution_contract.descriptor')


def validate_ticket_semantics(
    ticket: Mapping[str, Any],
    execution_contract: Mapping[str, Any],
    *,
    strict_jsonschema: bool = False,
    strict_ticket_profile: bool = False,
) -> List[str]:
    """Validate v0.3 scoped-ticket semantics against an execution contract.

    This is a local/static check. It does not decide trust, authorization,
    revocation, runtime enforcement, or whether execution actually occurred.
    """
    validate_ticket_schema(ticket, strict_jsonschema=strict_jsonschema)

    profile = str(ticket.get('ticket_profile') or '')
    if profile not in TICKET_PROFILES:
        raise TicketSemanticError(f'unsupported ticket_profile: {profile}')

    semantics = _require_mapping(ticket.get('ticket_semantics'), 'ticket.ticket_semantics')
    consumable = bool(semantics.get('consumable_by_runtime'))
    kind = str(semantics.get('kind') or '')
    if profile == 'review_record' and consumable:
        raise TicketSemanticError('review_record tickets must not be runtime-consumable')
    if profile == 'scoped_execution_ticket' and (not consumable or kind != 'runtime_consumable_scoped_ticket'):
        raise TicketSemanticError('scoped_execution_ticket must declare runtime_consumable_scoped_ticket semantics')
    if bool(semantics.get('default_transferable')):
        raise TicketSemanticError('scoped tickets must not be transferable by default')

    approval = _require_mapping(ticket.get('approval'), 'ticket.approval')
    approval_status = str(approval.get('status') or '')
    if profile == 'scoped_execution_ticket' and approval_status not in CONSUMABLE_APPROVAL_STATUSES:
        raise TicketSemanticError(f'scoped ticket is not approved for runtime consumption: {approval_status}')

    contract_descriptor = artifact_descriptor(execution_contract)
    linked_descriptor = dict(_linked_execution_contract_descriptor(ticket))
    if linked_descriptor != contract_descriptor:
        raise TicketSemanticError('ticket execution_contract descriptor mismatch')

    integrity = _require_mapping(ticket.get('integrity'), 'ticket.integrity')
    if str(integrity.get('ticket_binds_execution_contract_digest') or '') != contract_descriptor['digest']:
        raise TicketSemanticError('ticket integrity execution_contract digest mismatch')

    target_binding = _require_mapping(execution_contract.get('target_binding'), 'execution_contract.target_binding')
    scope_status = _legacy_execution_contract_scope_status(execution_contract)
    _ticket_validity_window(ticket)
    execution_shape = _require_mapping(execution_contract.get('execution_shape'), 'execution_contract.execution_shape')
    execution_bounds = _require_mapping(execution_contract.get('execution_bounds'), 'execution_contract.execution_bounds')
    execution_limits = _require_mapping(ticket.get('execution_limits'), 'ticket.execution_limits')
    scope_binding = _require_mapping(ticket.get('scope_binding'), 'ticket.scope_binding')
    spend_limits = _require_mapping(ticket.get('spend_limits'), 'ticket.spend_limits')

    contract_target_host = str(target_binding.get('target_host') or '')
    ticket_target_host = str(scope_binding.get('target_host') or '')
    if ticket_target_host != contract_target_host:
        raise TicketSemanticError('ticket target_host drift from execution_contract')

    target_ref = str(scope_binding.get('target_ref') or '')
    if target_ref not in {contract_target_host, f'host:{contract_target_host}', str(target_binding.get('target') or '')}:
        raise TicketSemanticError('ticket target_ref drift from execution_contract')

    if str(scope_binding.get('tool') or '') != str(execution_shape.get('tool') or ''):
        raise TicketSemanticError('ticket tool drift from execution_contract')

    contract_mode = str(execution_bounds.get('mode') or '')
    ticket_mode = str(scope_binding.get('mode') or execution_limits.get('mode') or '')
    if _mode_level(ticket_mode) > _mode_level(contract_mode):
        raise TicketSemanticError('ticket mode escalates beyond execution_contract bounds')
    if str(execution_limits.get('mode') or '') != ticket_mode:
        raise TicketSemanticError('ticket execution_limits.mode must match scope_binding.mode')

    expected_args_digest = normalized_args_digest(execution_shape.get('normalized_args') or [])
    if str(scope_binding.get('normalized_args_digest') or '') != expected_args_digest:
        raise TicketSemanticError('ticket normalized_args_digest mismatch')

    contract_network = bool(execution_bounds.get('network_execution_allowed'))
    ticket_network = bool(spend_limits.get('network_execution_allowed'))
    if ticket_network and not contract_network:
        raise TicketSemanticError('ticket network execution exceeds execution_contract bounds')

    max_runs = int(execution_limits.get('max_runs') or 0)
    max_uses = int(spend_limits.get('max_uses') or 0)
    if max_uses > max_runs:
        raise TicketSemanticError('ticket spend_limits.max_uses exceeds execution_limits.max_runs')
    if bool(spend_limits.get('one_shot')) and max_uses != 1:
        raise TicketSemanticError('one_shot ticket must have max_uses=1')
    if strict_ticket_profile and bool(spend_limits.get('one_shot')) and max_runs != 1:
        raise TicketSemanticError('strict one_shot ticket must have execution_limits.max_runs=1')
    if bool(execution_limits.get('one_shot')) and not bool(spend_limits.get('one_shot')):
        raise TicketSemanticError('execution_limits.one_shot requires spend_limits.one_shot')

    expected_receipt = execution_contract.get('expected_receipt')
    if isinstance(expected_receipt, Mapping) and bool(expected_receipt.get('required')) and not bool(spend_limits.get('requires_receipt')):
        raise TicketSemanticError('execution_contract requires a receipt but ticket does not')
    if profile == 'scoped_execution_ticket' and not bool(spend_limits.get('requires_receipt')):
        raise TicketSemanticError('scoped execution tickets must require a receipt')
    if profile == 'scoped_execution_ticket' and not bool(spend_limits.get('requires_evidence_contract')):
        raise TicketSemanticError('scoped execution tickets must require an evidence contract')

    return [
        'ticket_profile_supported',
        'ticket_runtime_consumption_semantics',
        'ticket_binds_execution_contract',
        'ticket_scope_matches_execution_contract',
        f'execution_contract_target_in_scope_{scope_status}',
        'ticket_mode_within_execution_bounds',
        'ticket_tool_matches_execution_contract',
        'ticket_args_digest_matches_execution_contract',
        'ticket_spend_limits_within_execution_limits',
        'ticket_receipt_and_evidence_obligations',
        'ticket_validity_window_well_formed',
    ]


def explain_ticket(ticket: Mapping[str, Any]) -> str:
    """Return a concise human-readable explanation of an ExecutionTicket."""
    profile = str(ticket.get('ticket_profile') or 'unknown')
    semantics = json_mapping(ticket.get('ticket_semantics'))
    subject = json_mapping(ticket.get('subject_binding'))
    scope = json_mapping(ticket.get('scope_binding'))
    spend = json_mapping(ticket.get('spend_limits'))
    integrity = json_mapping(ticket.get('integrity'))
    non_claims = json_array(ticket.get('non_claims'))

    lines = [
        f"SCLite ExecutionTicket {ticket.get('schema_version') or 'unknown'}",
        '',
        f'Profile: {profile}',
        f"Runtime-consumable: {'yes' if semantics.get('consumable_by_runtime') else 'no'}",
        f"Target: {scope.get('target_ref') or scope.get('target_host') or 'unknown'}",
        f"Tool: {scope.get('tool') or 'unknown'}",
        f"Mode: {scope.get('mode') or 'unknown'}",
        f"Usable by runtime: {subject.get('usable_by_runtime') or 'unknown'}",
        f"Max uses: {spend.get('max_uses') if 'max_uses' in spend else 'unknown'}",
        f"Network execution allowed: {str(spend.get('network_execution_allowed')).lower() if 'network_execution_allowed' in spend else 'unknown'}",
        f"Requires receipt: {str(spend.get('requires_receipt')).lower() if 'requires_receipt' in spend else 'unknown'}",
        f"Requires evidence contract: {str(spend.get('requires_evidence_contract')).lower() if 'requires_evidence_contract' in spend else 'unknown'}",
        f"Binds execution_contract: sha256:{integrity.get('ticket_binds_execution_contract_digest') or 'unknown'}",
    ]
    if non_claims:
        lines.extend(['', 'Non-claims:'])
        lines.extend(f'- {claim}' for claim in non_claims)
    return '\n'.join(lines)


def ticket_summary(ticket: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a compact machine-readable scoped-ticket summary."""
    subject = json_mapping(ticket.get('subject_binding'))
    scope = json_mapping(ticket.get('scope_binding'))
    spend = json_mapping(ticket.get('spend_limits'))
    return {
        'ticket_id': ticket.get('ticket_id'),
        'schema_version': ticket.get('schema_version'),
        'ticket_profile': ticket.get('ticket_profile'),
        'usable_by_runtime': subject.get('usable_by_runtime'),
        'target_ref': scope.get('target_ref'),
        'target_host': scope.get('target_host'),
        'tool': scope.get('tool'),
        'mode': scope.get('mode'),
        'max_uses': spend.get('max_uses'),
        'requires_receipt': spend.get('requires_receipt'),
        'requires_evidence_contract': spend.get('requires_evidence_contract'),
    }


def _artifact_link_descriptor(value: Mapping[str, Any], link_name: str, label: str) -> Mapping[str, Any]:
    links = _require_mapping(value.get('links'), f'{label}.links')
    link = _require_mapping(links.get(link_name), f'{label}.links.{link_name}')
    return _require_mapping(link.get('descriptor'), f'{label}.links.{link_name}.descriptor')


def _assert_artifact_link(source: Mapping[str, Any], link_name: str, target: Mapping[str, Any], label: str, reason: str) -> None:
    if dict(_artifact_link_descriptor(source, link_name, label)) != artifact_descriptor(target):
        raise TicketUseVerificationError(reason)


def _runtime_matches_ticket(ticket: Mapping[str, Any], receipt: Mapping[str, Any]) -> bool:
    subject = _require_mapping(ticket.get('subject_binding'), 'ticket.subject_binding')
    runtime = _require_mapping(receipt.get('runtime'), 'receipt.runtime')
    expected = str(subject.get('usable_by_runtime') or '')
    if not expected:
        return False
    candidates = {
        str(runtime.get('runtime_ref') or ''),
        str(runtime.get('id') or ''),
        str(runtime.get('name') or ''),
    }
    if expected.startswith('runtime:'):
        candidates.add('runtime:' + str(runtime.get('name') or ''))
    return expected in candidates


def _as_int(value: Any, label: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise TicketUseVerificationError(f'{label} must be an integer') from exc


def _parse_offset_aware_rfc3339(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise TicketUseVerificationError(f'{label} must be an offset-aware RFC3339 timestamp')
    normalized = value[:-1] + '+00:00' if value.endswith('Z') else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise TicketUseVerificationError(f'{label} must be an offset-aware RFC3339 timestamp') from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TicketUseVerificationError(f'{label} must be an offset-aware RFC3339 timestamp')
    return parsed


def _ticket_validity_window(ticket: Mapping[str, Any]) -> tuple[datetime, datetime]:
    validity = _require_mapping(ticket.get('validity'), 'ticket.validity')
    not_before = _parse_offset_aware_rfc3339(
        validity.get('not_before'),
        'ticket.validity.not_before',
    )
    not_after = _parse_offset_aware_rfc3339(
        validity.get('not_after'),
        'ticket.validity.not_after',
    )
    if not_before > not_after:
        raise TicketUseVerificationError('ticket validity not_before is after not_after')
    return not_before, not_after


def _legacy_execution_contract_scope_status(execution_contract: Mapping[str, Any]) -> str:
    target_binding = _require_mapping(
        execution_contract.get('target_binding'),
        'execution_contract.target_binding',
    )
    target_in_scope = target_binding.get('target_in_scope')
    if target_in_scope is False:
        raise TicketUseVerificationError('execution_contract target_in_scope is explicitly false')
    return 'operator_asserted' if target_in_scope is True else 'not_checked'


def _receipt_within_ticket_window_status(
    ticket: Mapping[str, Any],
    receipt: Mapping[str, Any],
    *,
    receipt_status: str,
) -> tuple[str, str]:
    not_before, not_after = _ticket_validity_window(ticket)
    execution = _require_mapping(receipt.get('execution'), 'receipt.execution')
    started_raw = execution.get('started_at')
    ended_raw = execution.get('ended_at')
    if started_raw is None or ended_raw is None:
        return (
            'review',
            'receipt execution timestamps are missing; ticket validity was not fully checked',
        )
    started_at = _parse_offset_aware_rfc3339(started_raw, 'receipt.execution.started_at')
    ended_at = _parse_offset_aware_rfc3339(ended_raw, 'receipt.execution.ended_at')
    if started_at > ended_at:
        raise TicketUseVerificationError('receipt execution started_at is after ended_at')
    if started_at < not_before or ended_at > not_after:
        raise TicketUseVerificationError('receipt execution interval is outside ticket validity window')
    if receipt_status in BLOCKED_RECEIPT_STATUSES:
        return (
            'review',
            'receipt is non-executed/blocked; ticket validity is not an execution pass',
        )
    return ('passed', 'receipt execution interval is within ticket validity window')


def _claim_text(claim: Mapping[str, Any]) -> str:
    parts = [claim.get('claim_type'), claim.get('id'), claim.get('statement')]
    return ' '.join(str(part or '').lower() for part in parts)


def _claim_has_marker(claim: Mapping[str, Any], markers: set[str]) -> bool:
    text = _claim_text(claim)
    return any(marker in text for marker in markers)


def _claim_requires_completed_execution(claim: Mapping[str, Any], *, allow_text_markers: bool = True) -> bool:
    return bool(claim.get('requires_completed_execution')) or (
        allow_text_markers and _claim_has_marker(claim, EXECUTION_CLAIM_MARKERS)
    )


def _claim_requires_network_execution(claim: Mapping[str, Any], *, allow_text_markers: bool = True) -> bool:
    return bool(claim.get('requires_network_execution')) or bool(claim.get('requires_live_execution')) or (
        allow_text_markers and _claim_has_marker(claim, NETWORK_CLAIM_MARKERS)
    )


def verify_ticket_use(
    ticket: Mapping[str, Any],
    execution_contract: Mapping[str, Any],
    receipt: Mapping[str, Any],
    evidence_contract: Mapping[str, Any] | None = None,
    *,
    strict_jsonschema: bool = False,
    strict_ticket_profile: bool = False,
    strict_evidence_claims: bool = False,
) -> Dict[str, Any]:
    """Verify that receipt/evidence claims stay inside a scoped ticket.

    This is the first static Receipt-Bounded Evidence gate for v0.3.5. It
    verifies local artifact bindings and conservative receipt/evidence limits;
    it does not execute tools, decide trust, prove legal authorization, or
    attest that a runtime enforced the ticket.
    """
    validate_ticket_semantics(
        ticket,
        execution_contract,
        strict_jsonschema=strict_jsonschema,
        strict_ticket_profile=strict_ticket_profile,
    )
    schema_ref = str(receipt.get('schema_ref') or '')
    if schema_ref:
        validate_artifact(dict(receipt), schema_ref, strict_jsonschema=strict_jsonschema)

    _assert_artifact_link(receipt, 'execution_ticket', ticket, 'receipt', 'receipt-ticket descriptor mismatch')
    _assert_artifact_link(receipt, 'execution_contract', execution_contract, 'receipt', 'receipt-execution_contract descriptor mismatch')

    if not _runtime_matches_ticket(ticket, receipt):
        raise TicketUseVerificationError('receipt runtime does not match ticket subject_binding.usable_by_runtime')

    scope = _require_mapping(ticket.get('scope_binding'), 'ticket.scope_binding')
    limits = _require_mapping(ticket.get('execution_limits'), 'ticket.execution_limits')
    spend = _require_mapping(ticket.get('spend_limits'), 'ticket.spend_limits')
    receipt_runtime = _require_mapping(receipt.get('runtime'), 'receipt.runtime')
    receipt_execution = _require_mapping(receipt.get('execution'), 'receipt.execution')
    outcome = _require_mapping(receipt.get('outcome'), 'receipt.outcome')
    scope_status = _legacy_execution_contract_scope_status(execution_contract)

    ticket_mode = str(scope.get('mode') or limits.get('mode') or '')
    receipt_mode = str(receipt_runtime.get('mode') or '')
    if _mode_level(receipt_mode) > _mode_level(ticket_mode):
        raise TicketUseVerificationError('receipt runtime mode exceeds ticket mode')
    dry_run_receipt_statuses = DRY_RUN_RECEIPT_STATUSES | BLOCKED_RECEIPT_STATUSES
    if ticket_mode == 'dry_run' and str(outcome.get('status') or '') not in dry_run_receipt_statuses:
        raise TicketUseVerificationError('dry-run ticket receipt must report a dry-run/non-executed outcome')

    if bool(receipt_execution.get('network_execution_performed')) and not bool(spend.get('network_execution_allowed')):
        raise TicketUseVerificationError('receipt reports network execution forbidden by ticket')

    max_uses = _as_int(spend.get('max_uses'), 'ticket.spend_limits.max_uses')
    ticket_use = receipt.get('ticket_use') if isinstance(receipt.get('ticket_use'), Mapping) else {}
    if strict_ticket_profile and not ticket_use:
        raise TicketUseVerificationError('strict ticket profile requires receipt.ticket_use')
    if ticket_use:
        if str(ticket_use.get('ticket_id') or '') != str(ticket.get('ticket_id') or ''):
            raise TicketUseVerificationError('receipt ticket_use.ticket_id mismatch')
        consumed_by_runtime = str(ticket_use.get('consumed_by_runtime') or '')
        expected_runtime = str(_require_mapping(ticket.get('subject_binding'), 'ticket.subject_binding').get('usable_by_runtime') or '')
        if strict_ticket_profile and not consumed_by_runtime:
            raise TicketUseVerificationError('strict ticket profile requires receipt.ticket_use.consumed_by_runtime')
        if consumed_by_runtime and consumed_by_runtime != expected_runtime:
            raise TicketUseVerificationError('receipt ticket_use.consumed_by_runtime mismatch')
        use_count = _as_int(ticket_use.get('use_count'), 'receipt.ticket_use.use_count')
        if use_count < 1 or use_count > max_uses:
            raise TicketUseVerificationError('receipt ticket use_count exceeds ticket max_uses')
    elif max_uses < 1:
        raise TicketUseVerificationError('ticket max_uses must permit at least one receipt')

    executed_count = _as_int(
        receipt_execution.get('executed_command_count', 0),
        'receipt.execution.executed_command_count',
    )
    if bool(spend.get('one_shot')) and executed_count > _as_int(limits.get('max_runs'), 'ticket.execution_limits.max_runs'):
        raise TicketUseVerificationError('receipt executed command count exceeds ticket execution limit')
    if strict_ticket_profile and bool(spend.get('one_shot')) and executed_count > 1:
        raise TicketUseVerificationError('strict one_shot receipt executed more than one command')

    checks = [
        'ticket_semantics_valid',
        'receipt_binds_ticket',
        'receipt_binds_execution_contract',
        'receipt_runtime_matches_ticket',
        'receipt_mode_within_ticket',
        'receipt_network_within_ticket',
        'receipt_use_within_ticket',
        'receipt_within_ticket_validity',
    ]

    receipt_status = str(outcome.get('status') or '').lower()
    network_performed = bool(receipt_execution.get('network_execution_performed'))
    ticket_time_status, ticket_time_detail = _receipt_within_ticket_window_status(
        ticket,
        receipt,
        receipt_status=receipt_status,
    )

    evidence_checks: List[str] = []
    if bool(spend.get('requires_evidence_contract')) and evidence_contract is None:
        raise TicketUseVerificationError('ticket requires an evidence contract but none was provided')
    if evidence_contract is not None:
        evidence_schema_ref = str(evidence_contract.get('schema_ref') or '')
        if evidence_schema_ref:
            validate_artifact(dict(evidence_contract), evidence_schema_ref, strict_jsonschema=strict_jsonschema)
        _assert_artifact_link(evidence_contract, 'execution_receipt', receipt, 'evidence_contract', 'evidence-receipt descriptor mismatch')
        _assert_artifact_link(evidence_contract, 'execution_ticket', ticket, 'evidence_contract', 'evidence-ticket descriptor mismatch')

        claims = evidence_contract.get('claims')
        if not isinstance(claims, list) or not claims:
            raise TicketUseVerificationError('evidence_contract.claims must be a non-empty array')
        for index, claim in enumerate(claims):
            if not isinstance(claim, Mapping):
                raise TicketUseVerificationError(f'evidence_contract.claims[{index}] must be an object')
            if claim.get('bounded_by_receipt') is not True:
                raise TicketUseVerificationError(f'evidence_contract.claims[{index}] is not receipt-bounded')
            source_receipt_id = str(claim.get('source_receipt_id') or '')
            if not source_receipt_id:
                raise TicketUseVerificationError(f'evidence_contract.claims[{index}] must declare source_receipt_id')
            if source_receipt_id != str(receipt.get('receipt_id') or ''):
                raise TicketUseVerificationError(f'evidence_contract.claims[{index}] source_receipt_id mismatch')
            if strict_evidence_claims and _claim_has_marker(claim, EXECUTION_CLAIM_MARKERS) and not bool(claim.get('requires_completed_execution')):
                raise TicketUseVerificationError(f'evidence_contract.claims[{index}] uses legacy execution text markers in strict evidence profile')
            if strict_evidence_claims and _claim_has_marker(claim, NETWORK_CLAIM_MARKERS) and not (
                bool(claim.get('requires_network_execution')) or bool(claim.get('requires_live_execution'))
            ):
                raise TicketUseVerificationError(f'evidence_contract.claims[{index}] uses legacy network text markers in strict evidence profile')
            if strict_evidence_claims and str(claim.get('claim_type') or '') not in {
                'receipt_bounded_dry_run', 'receipt_bounded_execution', 'fixture_review_observation'
            }:
                raise TicketUseVerificationError(f'evidence_contract.claims[{index}] has unsupported strict claim_type')
            claim_type = str(claim.get('claim_type') or '')
            if strict_evidence_claims and claim_type == 'receipt_bounded_execution' and claim.get('requires_completed_execution') is not True:
                raise TicketUseVerificationError(f'evidence_contract.claims[{index}] execution claim must require completed execution')
            if strict_evidence_claims and claim_type == 'receipt_bounded_execution' and receipt_status not in COMPLETED_RECEIPT_STATUSES:
                raise TicketUseVerificationError(f'evidence_contract.claims[{index}] execution claim requires completed receipt status')
            if strict_evidence_claims and claim_type in {'receipt_bounded_dry_run', 'fixture_review_observation'} and any(
                bool(claim.get(field)) for field in ('requires_completed_execution', 'requires_network_execution', 'requires_live_execution')
            ):
                raise TicketUseVerificationError(f'evidence_contract.claims[{index}] non-execution claim cannot require execution')
            if strict_evidence_claims and claim_type == 'receipt_bounded_dry_run' and receipt_status not in dry_run_receipt_statuses:
                raise TicketUseVerificationError(f'evidence_contract.claims[{index}] dry-run claim requires dry-run/non-executed receipt')
            if strict_evidence_claims and claim_type == 'receipt_bounded_dry_run' and executed_count != 0:
                raise TicketUseVerificationError(f'evidence_contract.claims[{index}] dry-run claim requires zero executed commands')
            if _claim_requires_completed_execution(claim, allow_text_markers=not strict_evidence_claims) and receipt_status in BLOCKED_RECEIPT_STATUSES:
                raise TicketUseVerificationError(f'evidence_contract.claims[{index}] requires completed execution beyond receipt status')
            if _claim_requires_completed_execution(claim, allow_text_markers=not strict_evidence_claims) and executed_count == 0:
                raise TicketUseVerificationError(f'evidence_contract.claims[{index}] requires executed commands beyond receipt')
            if _claim_requires_network_execution(claim, allow_text_markers=not strict_evidence_claims) and not network_performed:
                raise TicketUseVerificationError(f'evidence_contract.claims[{index}] requires network execution beyond receipt')
            text = _claim_text(claim)
            if ticket_mode == 'dry_run' and ('live_vulnerability' in text or 'confirmed_vulnerability' in text):
                raise TicketUseVerificationError(f'evidence_contract.claims[{index}] exceeds dry-run ticket evidence bounds')
        if ticket_mode == 'dry_run':
            non_claims = json_array(evidence_contract.get('non_claims'))
            if 'does_not_claim_live_vulnerability_evidence' not in {str(item) for item in non_claims}:
                raise TicketUseVerificationError('dry-run evidence contract must disclaim live vulnerability evidence')
        replay = _require_mapping(evidence_contract.get('replay'), 'evidence_contract.replay')
        if bool(replay.get('live_execution_required')) and not bool(spend.get('network_execution_allowed')):
            raise TicketUseVerificationError('evidence replay requires live execution forbidden by ticket')
        evidence_checks = [
            'evidence_binds_receipt',
            'evidence_binds_ticket',
            'evidence_claims_bounded_by_receipt',
            'evidence_replay_within_ticket',
        ]
        checks.extend(evidence_checks)

    status = 'passed'
    review_reasons: List[str] = []
    if scope_status != 'operator_asserted':
        status = 'review'
        review_reasons.append('execution_contract target_in_scope is not checked')
    if ticket_time_status != 'passed':
        status = 'review'
        review_reasons.append(ticket_time_detail)

    return {
        'status': status,
        'checks': checks,
        'ticket_id': ticket.get('ticket_id'),
        'receipt_id': receipt.get('receipt_id'),
        'evidence_contract_id': evidence_contract.get('evidence_contract_id') if evidence_contract else None,
        'summary': {
            'ticket': ticket_summary(ticket),
            'receipt_status': outcome.get('status'),
            'receipt_runtime': receipt_runtime.get('runtime_ref') or receipt_runtime.get('name'),
            'evidence_checks': evidence_checks,
            'scope_status': scope_status,
            'ticket_validity_status': ticket_time_status,
        },
        'detail': '; '.join(review_reasons),
    }


def verify_ticket_use_profile(
    artifacts_by_role: Mapping[str, Mapping[str, Any]],
    *,
    strict_jsonschema: bool = False,
    strict_ticket_profile: bool = False,
    strict_evidence_claims: bool = False,
) -> Dict[str, Any]:
    """Evaluate ticket-use verification for a lifecycle artifact set.

    The profile is intentionally static. It consumes already-present lifecycle
    artifacts and reports whether v0.3 receipt-bounded evidence was actually
    verified. It does not execute tools or make runtime admission decisions.
    """

    ticket = artifacts_by_role.get('execution_ticket')
    if not isinstance(ticket, Mapping):
        return {
            'status': 'review',
            'applicability': 'not_applicable',
            'detail': 'ticket-use verification requires an execution_ticket artifact',
            'checks': [],
        }
    if str(ticket.get('schema_version') or '') != 'v0.3':
        return {
            'status': 'review',
            'applicability': 'not_applicable',
            'detail': 'ticket-use verification requires execution_ticket.v0.3 artifacts',
            'ticket_id': ticket.get('ticket_id'),
            'checks': [],
        }

    missing = [
        role
        for role in ('policy_decision', 'execution_contract', 'execution_receipt', 'evidence_contract')
        if not isinstance(artifacts_by_role.get(role), Mapping)
    ]
    if missing:
        return {
            'status': 'review',
            'applicability': 'incomplete',
            'detail': 'ticket-use verification missing lifecycle artifacts: ' + ', '.join(missing),
            'ticket_id': ticket.get('ticket_id'),
            'checks': [],
        }

    policy_scope = artifacts_by_role['policy_decision'].get('scope')
    if not isinstance(policy_scope, Mapping):
        return {
            'status': 'review',
            'applicability': 'verified',
            'detail': 'policy_decision target_in_scope is not checked',
            'ticket_id': ticket.get('ticket_id'),
            'checks': [],
        }
    policy_target_in_scope = policy_scope.get('target_in_scope')
    if policy_target_in_scope is False:
        return {
            'status': 'fail',
            'applicability': 'verified',
            'detail': 'policy_decision target_in_scope is explicitly false',
            'ticket_id': ticket.get('ticket_id'),
            'checks': [],
        }

    try:
        result = verify_ticket_use(
            ticket,
            artifacts_by_role['execution_contract'],
            artifacts_by_role['execution_receipt'],
            artifacts_by_role['evidence_contract'],
            strict_jsonschema=strict_jsonschema,
            strict_ticket_profile=strict_ticket_profile,
            strict_evidence_claims=strict_evidence_claims,
        )
    except (TicketSemanticError, TicketUseVerificationError, JsonSchemaValidationError) as exc:
        return {
            'status': 'fail',
            'applicability': 'verified',
            'detail': str(exc),
            'ticket_id': ticket.get('ticket_id'),
            'checks': [],
        }

    if result.get('status') != 'passed' or policy_target_in_scope is not True:
        detail = str(result.get('detail') or '')
        if policy_target_in_scope is not True:
            detail = '; '.join(filter(None, [
                detail,
                'policy_decision target_in_scope is not checked',
            ]))
        return {
            **result,
            'status': 'review',
            'applicability': 'verified',
            'detail': detail or 'ticket-use verification is incomplete',
        }
    return {
        **result,
        'status': 'pass',
        'applicability': 'verified',
        'detail': 'ticket-use verification passed',
    }
