from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Mapping, Sequence

from .artifacts import JsonSchemaValidationError, validate_artifact
from .integrity import artifact_descriptor

SCOPED_TICKET_SCHEMA_REF = 'schemas/execution_ticket.v0.3.schema.json'
TICKET_PROFILES = {'review_record', 'scoped_execution_ticket', 'external_capability_ref'}
CONSUMABLE_APPROVAL_STATUSES = {'approved_for_dry_run', 'approved'}


class TicketSemanticError(ValueError):
    """Raised when an ExecutionTicket is well-shaped but semantically unsafe."""


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


def validate_ticket_semantics(ticket: Mapping[str, Any], execution_contract: Mapping[str, Any], *, strict_jsonschema: bool = False) -> List[str]:
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
        'ticket_mode_within_execution_bounds',
        'ticket_tool_matches_execution_contract',
        'ticket_args_digest_matches_execution_contract',
        'ticket_spend_limits_within_execution_limits',
        'ticket_receipt_and_evidence_obligations',
    ]


def explain_ticket(ticket: Mapping[str, Any]) -> str:
    """Return a concise human-readable explanation of an ExecutionTicket."""
    profile = str(ticket.get('ticket_profile') or 'unknown')
    semantics = ticket.get('ticket_semantics') if isinstance(ticket.get('ticket_semantics'), Mapping) else {}
    subject = ticket.get('subject_binding') if isinstance(ticket.get('subject_binding'), Mapping) else {}
    scope = ticket.get('scope_binding') if isinstance(ticket.get('scope_binding'), Mapping) else {}
    spend = ticket.get('spend_limits') if isinstance(ticket.get('spend_limits'), Mapping) else {}
    integrity = ticket.get('integrity') if isinstance(ticket.get('integrity'), Mapping) else {}
    non_claims = ticket.get('non_claims') if isinstance(ticket.get('non_claims'), list) else []

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
    subject = ticket.get('subject_binding') if isinstance(ticket.get('subject_binding'), Mapping) else {}
    scope = ticket.get('scope_binding') if isinstance(ticket.get('scope_binding'), Mapping) else {}
    spend = ticket.get('spend_limits') if isinstance(ticket.get('spend_limits'), Mapping) else {}
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
