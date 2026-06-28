from __future__ import annotations

import pytest

from sclite import (
    build_watchdog_decision,
    validate_watchdog_decision,
    watchdog_decision_descriptor,
    watchdog_decision_digest,
)
from sclite.artifacts import JsonSchemaValidationError

HEX_A = 'a' * 64
HEX_B = 'b' * 64
HEX_C = 'c' * 64


def _observation() -> dict:
    return {
        'record_id': 'wd-1',
        'schema': 'rexecop.watchdog_record.v0.1',
        'observation': 'stuck_operation',
        'observed_at': '2026-06-28T12:00:00+00:00',
        'digest': HEX_A,
    }


def _admission(*, allowed: bool = True, outcome: str = 'allowed') -> dict:
    return {
        'request_digest': 'sha256:' + HEX_B,
        'admission_digest': 'sha256:' + HEX_C,
        'admission': {'allowed': allowed, 'outcome': outcome},
    }


def test_watchdog_decision_binds_observation_admission_and_operation() -> None:
    artifact = build_watchdog_decision(
        decision_id='watchdog-1',
        decision='block_autostart',
        reason='stale_active_operation',
        decided_at='2026-06-28T12:00:00+00:00',
        source='rexecop.watchdog',
        observation=_observation(),
        admission=_admission(),
        affected={'operation_id': 'op-1'},
        domain_authority='runtime-fixture',
    )

    assert artifact['observation']['digest'] == 'sha256:' + HEX_A
    assert artifact['affected']['operation_id'] == 'op-1'
    assert artifact['authority'] == {
        'truth_layer': 'sclite',
        'supervisor': 'rexecop',
        'policy_authority': 'govengine',
        'domain_authority': 'runtime-fixture',
        'execution_authority': 'rexecop',
    }
    assert watchdog_decision_digest(artifact).startswith('sha256:')
    assert watchdog_decision_descriptor(artifact)['artifact_type'] == 'watchdog_decision'


def test_dead_letter_watchdog_decision_requires_allowed_admission() -> None:
    with pytest.raises(ValueError, match='requires allowed admission'):
        build_watchdog_decision(
            decision_id='watchdog-1',
            decision='move_to_dead_letter',
            reason='retry_budget_exhausted',
            decided_at='2026-06-28T12:00:00+00:00',
            source='rexecop.watchdog',
            observation={**_observation(), 'observation': 'inbox_item'},
            admission=_admission(allowed=False, outcome='blocked'),
            affected={'inbox_item_name': 'job-1.json'},
            domain_authority='runtime-fixture',
        )


def test_watchdog_decision_requires_affected_reference_for_action() -> None:
    with pytest.raises(ValueError, match='requires operation_id'):
        build_watchdog_decision(
            decision_id='watchdog-1',
            decision='block_autostart',
            reason='stale_active_operation',
            decided_at='2026-06-28T12:00:00+00:00',
            source='rexecop.watchdog',
            observation=_observation(),
            admission=_admission(),
            affected={},
            domain_authority='runtime-fixture',
        )

    with pytest.raises(ValueError, match='requires inbox_item_name'):
        build_watchdog_decision(
            decision_id='watchdog-2',
            decision='retry_later',
            reason='inbox_processing_failed',
            decided_at='2026-06-28T12:00:00+00:00',
            source='rexecop.watchdog',
            observation={**_observation(), 'observation': 'inbox_item'},
            admission=_admission(),
            affected={},
            domain_authority='runtime-fixture',
        )


def test_watchdog_decision_schema_rejects_raw_payload() -> None:
    artifact = build_watchdog_decision(
        decision_id='watchdog-1',
        decision='block_autostart',
        reason='stale_active_operation',
        decided_at='2026-06-28T12:00:00+00:00',
        source='rexecop.watchdog',
        observation=_observation(),
        admission=_admission(),
        affected={'operation_id': 'op-1'},
        domain_authority='runtime-fixture',
    )
    artifact['observation']['payload'] = {'raw': 'forbidden'}

    with pytest.raises(JsonSchemaValidationError, match='unexpected fields'):
        validate_watchdog_decision(artifact)
