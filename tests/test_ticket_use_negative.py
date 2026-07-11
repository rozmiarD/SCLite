from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from sclite.integrity import artifact_descriptor
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


def _scoped_artifacts() -> dict[str, dict]:
    return {
        'execution_contract': _contract(),
        'execution_ticket': _ticket(),
        'execution_receipt': _receipt(),
        'evidence_contract': _evidence(),
    }


def _rebind_scoped_artifacts(artifacts: dict[str, dict]) -> None:
    contract = artifacts['execution_contract']
    ticket = artifacts['execution_ticket']
    receipt = artifacts['execution_receipt']
    evidence = artifacts['evidence_contract']
    contract_descriptor = artifact_descriptor(contract)
    ticket['links']['execution_contract']['descriptor'] = contract_descriptor
    ticket['integrity']['ticket_binds_execution_contract_digest'] = contract_descriptor['digest']
    ticket_descriptor = artifact_descriptor(ticket)
    receipt['links']['execution_contract']['descriptor'] = contract_descriptor
    receipt['links']['execution_ticket']['descriptor'] = ticket_descriptor
    receipt_descriptor = artifact_descriptor(receipt)
    evidence['links']['execution_ticket']['descriptor'] = ticket_descriptor
    evidence['links']['execution_receipt']['descriptor'] = receipt_descriptor


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


def test_ticket_use_rejects_structured_network_overclaim_without_text_marker() -> None:
    evidence = _evidence()
    evidence['claims'][0]['claim_type'] = 'bounded_observation'
    evidence['claims'][0]['statement'] = 'public-safe dry-run observation only'
    evidence['claims'][0]['requires_network_execution'] = True
    with pytest.raises(TicketUseVerificationError, match='network execution beyond receipt'):
        verify_ticket_use(_ticket(), _contract(), _receipt(), evidence)


def test_ticket_use_keeps_legacy_text_marker_compatibility() -> None:
    evidence = _evidence()
    evidence['claims'][0]['claim_type'] = 'bounded_observation'
    evidence['claims'][0]['statement'] = 'operator says completed_execution happened'
    evidence['claims'][0]['requires_completed_execution'] = False
    with pytest.raises(TicketUseVerificationError, match='executed commands beyond receipt'):
        verify_ticket_use(_ticket(), _contract(), _receipt(), evidence)


def test_strict_evidence_profile_rejects_legacy_text_marker_fallback() -> None:
    evidence = _evidence()
    evidence['claims'][0]['claim_type'] = 'bounded_observation'
    evidence['claims'][0]['statement'] = 'operator says completed_execution happened'
    evidence['claims'][0]['requires_completed_execution'] = False
    with pytest.raises(TicketUseVerificationError, match='legacy execution text markers'):
        verify_ticket_use(
            _ticket(),
            _contract(),
            _receipt(),
            evidence,
            strict_evidence_claims=True,
        )


def test_strict_execution_claim_requires_completed_execution_flag() -> None:
    evidence = _evidence()
    evidence['claims'][0].update({
        'claim_type': 'receipt_bounded_execution',
        'statement': 'Production host fully compromised',
        'requires_completed_execution': False,
        'requires_network_execution': False,
        'requires_live_execution': False,
    })
    with pytest.raises(TicketUseVerificationError, match='must require completed execution'):
        verify_ticket_use(_ticket(), _contract(), _receipt(), evidence, strict_evidence_claims=True)


def test_strict_dry_run_claim_rejects_execution_flags() -> None:
    evidence = _evidence()
    evidence['claims'][0]['requires_completed_execution'] = True
    with pytest.raises(TicketUseVerificationError, match='non-execution claim cannot require execution'):
        verify_ticket_use(_ticket(), _contract(), _receipt(), evidence, strict_evidence_claims=True)


def test_strict_execution_claim_rejects_dry_run_receipt() -> None:
    receipt = _receipt()
    receipt['outcome']['status'] = 'dry_run'
    receipt['execution']['executed_command_count'] = 1
    evidence = _evidence()
    evidence['links']['execution_receipt']['descriptor'] = artifact_descriptor(receipt)
    evidence['claims'][0].update({
        'claim_type': 'receipt_bounded_execution',
        'requires_completed_execution': True,
        'requires_network_execution': False,
        'requires_live_execution': False,
    })
    with pytest.raises(TicketUseVerificationError, match='requires completed receipt status'):
        verify_ticket_use(_ticket(), _contract(), receipt, evidence, strict_ticket_profile=True, strict_evidence_claims=True)


def test_strict_dry_run_claim_requires_zero_executed_commands() -> None:
    receipt = _receipt()
    receipt['outcome']['status'] = 'dry_run'
    receipt['execution']['executed_command_count'] = 1
    evidence = _evidence()
    evidence['links']['execution_receipt']['descriptor'] = artifact_descriptor(receipt)
    with pytest.raises(TicketUseVerificationError, match='requires zero executed commands'):
        verify_ticket_use(_ticket(), _contract(), receipt, evidence, strict_ticket_profile=True, strict_evidence_claims=True)


@pytest.mark.parametrize('status', ['blocked', 'rejected', 'denied', 'failed'])
def test_strict_dry_run_claim_rejects_blocked_or_failed_receipt(status: str) -> None:
    receipt = _receipt()
    receipt['outcome']['status'] = status
    receipt['execution']['executed_command_count'] = 0
    evidence = _evidence()
    evidence['links']['execution_receipt']['descriptor'] = artifact_descriptor(receipt)
    with pytest.raises(TicketUseVerificationError, match='requires dry-run receipt status'):
        verify_ticket_use(
            _ticket(),
            _contract(),
            receipt,
            evidence,
            strict_ticket_profile=True,
            strict_evidence_claims=True,
        )


def test_strict_one_shot_profile_requires_single_max_run() -> None:
    ticket = _ticket()
    ticket['execution_limits']['max_runs'] = 2
    with pytest.raises(TicketSemanticError, match='strict one_shot ticket'):
        validate_ticket_semantics(ticket, _contract(), strict_ticket_profile=True)


def test_ticket_use_rejects_evidence_replay_live_execution_requirement() -> None:
    evidence = _evidence()
    evidence['replay']['live_execution_required'] = True
    with pytest.raises(TicketUseVerificationError, match='replay requires live execution forbidden by ticket'):
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


@pytest.mark.parametrize('strict_jsonschema', [False, True])
def test_ticket_use_rejects_explicitly_out_of_scope_contract(
    strict_jsonschema: bool,
) -> None:
    artifacts = _scoped_artifacts()
    artifacts['execution_contract']['target_binding']['target_in_scope'] = False
    _rebind_scoped_artifacts(artifacts)

    with pytest.raises(TicketUseVerificationError, match='target_in_scope is explicitly false'):
        verify_ticket_use(
            artifacts['execution_ticket'],
            artifacts['execution_contract'],
            artifacts['execution_receipt'],
            artifacts['evidence_contract'],
            strict_jsonschema=strict_jsonschema,
        )


@pytest.mark.parametrize('strict_jsonschema', [False, True])
def test_ticket_use_marks_unknown_scope_for_review(
    strict_jsonschema: bool,
) -> None:
    artifacts = _scoped_artifacts()
    del artifacts['execution_contract']['target_binding']['target_in_scope']
    _rebind_scoped_artifacts(artifacts)

    result = verify_ticket_use(
        artifacts['execution_ticket'],
        artifacts['execution_contract'],
        artifacts['execution_receipt'],
        artifacts['evidence_contract'],
        strict_jsonschema=strict_jsonschema,
    )

    assert result['status'] == 'review'
    assert result['summary']['scope_status'] == 'not_checked'


@pytest.mark.parametrize('strict_jsonschema', [False, True])
@pytest.mark.parametrize(
    ('validity', 'execution'),
    [
        (
            {
                'not_before': '2026-05-13T20:54:00+00:00',
                'not_after': '2026-05-14T20:54:00+00:00',
            },
            {
                'started_at': '2026-05-13T20:54:00+00:00',
                'ended_at': '2026-05-14T20:54:00+00:00',
            },
        ),
        (
            {
                'not_before': '2026-05-13T22:54:00+02:00',
                'not_after': '2026-05-14T22:54:00+02:00',
            },
            {
                'started_at': '2026-05-13T22:54:00+02:00',
                'ended_at': '2026-05-14T22:54:00+02:00',
            },
        ),
    ],
)
def test_ticket_use_accepts_exact_and_offset_aware_validity_boundaries(
    strict_jsonschema: bool,
    validity: dict[str, str],
    execution: dict[str, str],
) -> None:
    artifacts = _scoped_artifacts()
    artifacts['execution_ticket']['validity'] = validity
    artifacts['execution_receipt']['execution'].update(execution)
    _rebind_scoped_artifacts(artifacts)

    result = verify_ticket_use(
        artifacts['execution_ticket'],
        artifacts['execution_contract'],
        artifacts['execution_receipt'],
        artifacts['evidence_contract'],
        strict_jsonschema=strict_jsonschema,
    )

    assert result['status'] == 'passed'
    assert result['summary']['ticket_validity_status'] == 'passed'


@pytest.mark.parametrize('strict_jsonschema', [False, True])
@pytest.mark.parametrize(
    ('validity', 'execution', 'error'),
    [
        (
            {
                'not_before': '2026-05-13T20:54:00+00:00',
                'not_after': '2026-05-14T20:54:00+00:00',
            },
            {
                'started_at': '2026-05-13T20:53:59+00:00',
                'ended_at': '2026-05-13T21:05:00+00:00',
            },
            'outside ticket validity window',
        ),
        (
            {
                'not_before': '2026-05-13T20:54:00+00:00',
                'not_after': '2026-05-14T20:54:00+00:00',
            },
            {
                'started_at': '2026-05-13T21:05:00+00:00',
                'ended_at': '2026-05-14T20:54:01+00:00',
            },
            'outside ticket validity window',
        ),
        (
            {
                'not_before': '2026-05-13T20:54:00+00:00',
                'not_after': '2026-05-14T20:54:00+00:00',
            },
            {
                'started_at': '2026-05-13T20:53:59+00:00',
                'ended_at': '2026-05-14T20:54:01+00:00',
            },
            'outside ticket validity window',
        ),
        (
            {
                'not_before': '2026-05-14T20:54:00+00:00',
                'not_after': '2026-05-13T20:54:00+00:00',
            },
            {
                'started_at': '2026-05-13T21:05:00+00:00',
                'ended_at': '2026-05-13T21:05:00+00:00',
            },
            'not_before is after not_after',
        ),
        (
            {
                'not_before': '2026-05-13T20:54:00+00:00',
                'not_after': '2026-05-14T20:54:00+00:00',
            },
            {
                'started_at': '2026-05-13T21:06:00+00:00',
                'ended_at': '2026-05-13T21:05:00+00:00',
            },
            'started_at is after ended_at',
        ),
        (
            {
                'not_before': '2026-05-13T20:54:00',
                'not_after': '2026-05-14T20:54:00+00:00',
            },
            {
                'started_at': '2026-05-13T21:05:00+00:00',
                'ended_at': '2026-05-13T21:05:00+00:00',
            },
            'offset-aware RFC3339',
        ),
    ],
)
def test_ticket_use_rejects_invalid_or_out_of_window_receipt_intervals(
    strict_jsonschema: bool,
    validity: dict[str, str],
    execution: dict[str, str],
    error: str,
) -> None:
    artifacts = _scoped_artifacts()
    artifacts['execution_ticket']['validity'] = validity
    artifacts['execution_receipt']['execution'].update(execution)
    _rebind_scoped_artifacts(artifacts)

    with pytest.raises(TicketUseVerificationError, match=error):
        verify_ticket_use(
            artifacts['execution_ticket'],
            artifacts['execution_contract'],
            artifacts['execution_receipt'],
            artifacts['evidence_contract'],
            strict_jsonschema=strict_jsonschema,
        )


@pytest.mark.parametrize('strict_jsonschema', [False, True])
def test_ticket_use_marks_missing_receipt_timestamps_for_review(
    strict_jsonschema: bool,
) -> None:
    artifacts = _scoped_artifacts()
    artifacts['execution_receipt']['execution'].pop('started_at')
    artifacts['execution_receipt']['execution'].pop('ended_at')
    _rebind_scoped_artifacts(artifacts)

    result = verify_ticket_use(
        artifacts['execution_ticket'],
        artifacts['execution_contract'],
        artifacts['execution_receipt'],
        artifacts['evidence_contract'],
        strict_jsonschema=strict_jsonschema,
    )

    assert result['status'] == 'review'
    assert result['summary']['ticket_validity_status'] == 'review'
