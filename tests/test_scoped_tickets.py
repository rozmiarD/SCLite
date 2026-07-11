from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from sclite.artifacts import validate_artifact
from sclite.integrity import artifact_descriptor
from sclite.tickets import TicketSemanticError, TicketUseVerificationError, explain_ticket, normalized_args_digest, validate_ticket_semantics, verify_ticket_use

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
            'sclite.kernel_cli',
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
        [sys.executable, '-m', 'sclite.devtools', 'explain-ticket', str(FIXTURE / 'execution_ticket.json')],
        cwd=str(ROOT),
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert 'SCLite ExecutionTicket v0.3' in result.stdout
    assert 'Binds execution_contract: sha256:' in result.stdout


def test_verify_ticket_use_accepts_receipt_bounded_evidence_fixture() -> None:
    result = verify_ticket_use(_ticket(), _contract(), _receipt(), _evidence())
    assert result['status'] == 'passed'
    assert 'receipt_binds_ticket' in result['checks']
    assert 'evidence_claims_bounded_by_receipt' in result['checks']


def test_verify_ticket_use_rejects_receipt_ticket_drift() -> None:
    receipt = _receipt()
    receipt['links']['execution_ticket']['descriptor']['digest'] = '0' * 64
    with pytest.raises(TicketUseVerificationError, match='receipt-ticket descriptor mismatch'):
        verify_ticket_use(_ticket(), _contract(), receipt, _evidence())


def test_verify_ticket_use_rejects_runtime_drift() -> None:
    receipt = _receipt()
    receipt['runtime']['runtime_ref'] = 'runtime:other'
    receipt['runtime']['name'] = 'other'
    with pytest.raises(TicketUseVerificationError, match='runtime does not match'):
        verify_ticket_use(_ticket(), _contract(), receipt, _evidence())


def test_verify_ticket_use_rejects_live_receipt_for_dry_run_ticket() -> None:
    receipt = _receipt()
    receipt['runtime']['mode'] = 'live'
    receipt['outcome']['status'] = 'completed'
    with pytest.raises(TicketUseVerificationError, match='mode exceeds'):
        verify_ticket_use(_ticket(), _contract(), receipt, _evidence())


def test_verify_ticket_use_rejects_forbidden_network_execution() -> None:
    receipt = _receipt()
    receipt['execution']['network_execution_performed'] = True
    with pytest.raises(TicketUseVerificationError, match='network execution forbidden'):
        verify_ticket_use(_ticket(), _contract(), receipt, _evidence())


def test_verify_ticket_use_rejects_ticket_use_count_over_limit() -> None:
    receipt = _receipt()
    receipt['ticket_use']['use_count'] = 2
    with pytest.raises(TicketUseVerificationError, match='use_count exceeds'):
        verify_ticket_use(_ticket(), _contract(), receipt, _evidence())


def test_verify_ticket_use_requires_evidence_when_ticket_requires_it() -> None:
    with pytest.raises(TicketUseVerificationError, match='requires an evidence contract'):
        verify_ticket_use(_ticket(), _contract(), _receipt(), None)


def test_verify_ticket_use_rejects_unbounded_claims() -> None:
    evidence = _evidence()
    evidence['claims'][0]['bounded_by_receipt'] = False
    with pytest.raises(TicketUseVerificationError, match='not receipt-bounded'):
        verify_ticket_use(_ticket(), _contract(), _receipt(), evidence)


def test_verify_ticket_use_rejects_live_vulnerability_claims_for_dry_run() -> None:
    evidence = _evidence()
    evidence['claims'][0]['claim_type'] = 'confirmed_vulnerability'
    with pytest.raises(TicketUseVerificationError, match='exceeds dry-run'):
        verify_ticket_use(_ticket(), _contract(), _receipt(), evidence)


def test_verify_ticket_use_rejects_evidence_receipt_drift() -> None:
    evidence = _evidence()
    evidence['links']['execution_receipt']['descriptor']['digest'] = '0' * 64
    with pytest.raises(TicketUseVerificationError, match='evidence-receipt descriptor mismatch'):
        verify_ticket_use(_ticket(), _contract(), _receipt(), evidence)


def test_verify_ticket_use_requires_explicit_claim_source_receipt_id() -> None:
    evidence = _evidence()
    del evidence['claims'][0]['source_receipt_id']
    with pytest.raises(TicketUseVerificationError, match='must declare source_receipt_id'):
        verify_ticket_use(_ticket(), _contract(), _receipt(), evidence)


def test_verify_ticket_use_rejects_completed_claims_for_blocked_receipt() -> None:
    receipt = _receipt()
    receipt['outcome']['status'] = 'blocked'
    evidence = _evidence()
    evidence['links']['execution_receipt']['descriptor'] = artifact_descriptor(receipt)
    evidence['claims'][0]['requires_completed_execution'] = True
    with pytest.raises(TicketUseVerificationError, match='completed execution beyond receipt status'):
        verify_ticket_use(_ticket(), _contract(), receipt, evidence)


def test_verify_ticket_use_rejects_execution_claims_when_no_commands_executed() -> None:
    evidence = _evidence()
    evidence['claims'][0]['requires_completed_execution'] = True
    with pytest.raises(TicketUseVerificationError, match='executed commands beyond receipt'):
        verify_ticket_use(_ticket(), _contract(), _receipt(), evidence)


def test_verify_ticket_use_rejects_network_claims_when_no_network_performed() -> None:
    evidence = _evidence()
    evidence['claims'][0]['requires_network_execution'] = True
    with pytest.raises(TicketUseVerificationError, match='network execution beyond receipt'):
        verify_ticket_use(_ticket(), _contract(), _receipt(), evidence)


def test_verify_ticket_use_cli() -> None:
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'sclite.kernel_cli',
            'verify-ticket-use',
            str(FIXTURE / 'execution_ticket.json'),
            '--contract',
            str(FIXTURE / 'execution_contract.json'),
            '--receipt',
            str(FIXTURE / 'execution_receipt.json'),
            '--evidence-contract',
            str(FIXTURE / 'evidence_contract.json'),
        ],
        cwd=str(ROOT),
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith('ticket_use_ok:scoped-ticket-demo-001:scoped-ticket-receipt-demo-001:')
