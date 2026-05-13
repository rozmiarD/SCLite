from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from sclite.artifacts import validate_artifact
from sclite.tickets import TicketSemanticError, explain_ticket, normalized_args_digest, validate_ticket_semantics

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


def test_execution_ticket_v03_schema_validates_fixture() -> None:
    ticket = _ticket()
    validate_artifact(ticket, 'execution_ticket.v0.3')
    validate_artifact(ticket, 'execution_ticket.v0.3', strict_jsonschema=True)


def test_normalized_args_digest_is_stable() -> None:
    contract = _contract()
    expected = normalized_args_digest(contract['execution_shape']['normalized_args'])
    assert expected.startswith('sha256:')
    assert _ticket()['scope_binding']['normalized_args_digest'] == expected


def test_scoped_ticket_semantics_validate_fixture() -> None:
    checks = validate_ticket_semantics(_ticket(), _contract())
    assert 'ticket_scope_matches_execution_contract' in checks
    assert 'ticket_args_digest_matches_execution_contract' in checks
    assert 'ticket_receipt_and_evidence_obligations' in checks


def test_scoped_ticket_rejects_target_drift() -> None:
    ticket = _ticket()
    ticket['scope_binding']['target_host'] = 'other.example.com'
    with pytest.raises(TicketSemanticError, match='target_host drift'):
        validate_ticket_semantics(ticket, _contract())


def test_scoped_ticket_rejects_target_ref_drift() -> None:
    ticket = _ticket()
    ticket['scope_binding']['target_ref'] = 'host:other.example.com'
    with pytest.raises(TicketSemanticError, match='target_ref drift'):
        validate_ticket_semantics(ticket, _contract())


def test_scoped_ticket_rejects_mode_escalation() -> None:
    ticket = _ticket()
    ticket['scope_binding']['mode'] = 'live'
    ticket['execution_limits']['mode'] = 'live'
    with pytest.raises(TicketSemanticError, match='mode escalates'):
        validate_ticket_semantics(ticket, _contract())


def test_scoped_ticket_rejects_tool_drift() -> None:
    ticket = _ticket()
    ticket['scope_binding']['tool'] = 'nmap'
    with pytest.raises(TicketSemanticError, match='tool drift'):
        validate_ticket_semantics(ticket, _contract())


def test_scoped_ticket_rejects_args_digest_mismatch() -> None:
    ticket = _ticket()
    ticket['scope_binding']['normalized_args_digest'] = 'sha256:' + ('0' * 64)
    with pytest.raises(TicketSemanticError, match='normalized_args_digest mismatch'):
        validate_ticket_semantics(ticket, _contract())


def test_scoped_ticket_rejects_network_escalation() -> None:
    ticket = _ticket()
    ticket['spend_limits']['network_execution_allowed'] = True
    with pytest.raises(TicketSemanticError, match='network execution exceeds'):
        validate_ticket_semantics(ticket, _contract())


def test_scoped_ticket_rejects_missing_receipt_obligation() -> None:
    ticket = _ticket()
    ticket['spend_limits']['requires_receipt'] = False
    with pytest.raises(TicketSemanticError, match='requires a receipt'):
        validate_ticket_semantics(ticket, _contract())


def test_review_record_ticket_is_not_runtime_consumable() -> None:
    ticket = _ticket()
    ticket['ticket_profile'] = 'review_record'
    ticket['ticket_semantics']['kind'] = 'review_record'
    ticket['ticket_semantics']['consumable_by_runtime'] = True
    with pytest.raises(TicketSemanticError, match='review_record tickets must not be runtime-consumable'):
        validate_ticket_semantics(ticket, _contract())


def test_scoped_ticket_rejects_unapproved_status() -> None:
    ticket = _ticket()
    ticket['approval']['status'] = 'owner_approval_required'
    with pytest.raises(TicketSemanticError, match='not approved'):
        validate_ticket_semantics(ticket, _contract())


def test_explain_ticket_mentions_key_bounds() -> None:
    output = explain_ticket(_ticket())
    assert 'SCLite ExecutionTicket v0.3' in output
    assert 'Profile: scoped_execution_ticket' in output
    assert 'Runtime-consumable: yes' in output
    assert 'Target: host:example.com' in output
    assert 'Requires receipt: true' in output
    assert 'does_not_prove_legal_authorization' in output


def test_validate_ticket_cli_with_contract() -> None:
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'sclite.cli',
            'validate-ticket',
            str(FIXTURE / 'execution_ticket.json'),
            '--contract',
            str(FIXTURE / 'execution_contract.json'),
        ],
        cwd=str(ROOT),
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith('execution_ticket_ok:v0.3:scoped_execution_ticket:')


def test_explain_ticket_cli() -> None:
    result = subprocess.run(
        [sys.executable, '-m', 'sclite.cli', 'explain-ticket', str(FIXTURE / 'execution_ticket.json')],
        cwd=str(ROOT),
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert 'SCLite ExecutionTicket v0.3' in result.stdout
    assert 'Binds execution_contract: sha256:' in result.stdout
