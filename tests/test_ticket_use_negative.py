from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from sclite.tickets import TicketSemanticError, TicketUseVerificationError, validate_ticket_semantics, verify_ticket_use

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'sclite' / 'examples' / 'scoped-ticket-v0.3'


def _load(name: str) -> dict:
    value = json.loads((FIXTURE / name).read_text(encoding='utf-8'))
    assert isinstance(value, dict)
    return value


def _ticket() -> dict:
    return copy.deepcopy(_load('execution_ticket.json'))


def _contract() -> dict:
    return copy.deepcopy(_load('execution_contract.json'))


def _receipt() -> dict:
    return copy.deepcopy(_load('execution_receipt.json'))


def _evidence() -> dict:
    return copy.deepcopy(_load('evidence_contract.json'))


def test_ticket_use_rejects_dry_run_receipt_claiming_completed_live_execution() -> None:
    receipt = _receipt()
    receipt['runtime']['mode'] = 'live'
    receipt['outcome']['status'] = 'completed'
    with pytest.raises(TicketUseVerificationError, match='mode exceeds'):
        verify_ticket_use(_ticket(), _contract(), receipt, _evidence())


def test_ticket_use_rejects_evidence_completed_execution_overclaim() -> None:
    evidence = _evidence()
    evidence['claims'][0]['requires_completed_execution'] = True
    with pytest.raises(TicketUseVerificationError, match='executed commands beyond receipt'):
        verify_ticket_use(_ticket(), _contract(), _receipt(), evidence)


def test_ticket_use_rejects_evidence_live_execution_overclaim() -> None:
    evidence = _evidence()
    evidence['claims'][0]['requires_live_execution'] = True
    with pytest.raises(TicketUseVerificationError, match='network execution beyond receipt'):
        verify_ticket_use(_ticket(), _contract(), _receipt(), evidence)


def test_ticket_use_rejects_receipt_contract_digest_drift() -> None:
    receipt = _receipt()
    receipt['links']['execution_contract']['descriptor']['digest'] = '0' * 64
    with pytest.raises(TicketUseVerificationError, match='receipt-execution_contract descriptor mismatch'):
        verify_ticket_use(_ticket(), _contract(), receipt, _evidence())


def test_ticket_use_rejects_evidence_ticket_digest_drift() -> None:
    evidence = _evidence()
    evidence['links']['execution_ticket']['descriptor']['digest'] = '0' * 64
    with pytest.raises(TicketUseVerificationError, match='evidence-ticket descriptor mismatch'):
        verify_ticket_use(_ticket(), _contract(), _receipt(), evidence)


def test_ticket_semantics_reject_target_tool_and_args_drift() -> None:
    ticket = _ticket()
    ticket['scope_binding']['target_host'] = 'evil.example.net'
    with pytest.raises(TicketSemanticError, match='target_host drift'):
        validate_ticket_semantics(ticket, _contract())

    ticket = _ticket()
    ticket['scope_binding']['tool'] = 'curl'
    with pytest.raises(TicketSemanticError, match='tool drift'):
        validate_ticket_semantics(ticket, _contract())

    ticket = _ticket()
    ticket['scope_binding']['normalized_args_digest'] = 'sha256:' + ('0' * 64)
    with pytest.raises(TicketSemanticError, match='normalized_args_digest mismatch'):
        validate_ticket_semantics(ticket, _contract())
