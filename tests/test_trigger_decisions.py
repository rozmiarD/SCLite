from __future__ import annotations

import pytest

from sclite import (
    build_trigger_decision,
    trigger_decision_descriptor,
    trigger_decision_digest,
    validate_trigger_decision,
)
from sclite.artifacts import JsonSchemaValidationError


HEX_A = 'a' * 64
HEX_B = 'b' * 64
HEX_C = 'c' * 64
HEX_D = 'd' * 64


def _event() -> dict:
    return {
        'id': 'evt-1',
        'source': 'fixture-source',
        'type': 'fixture.state_observed',
        'subject': 'fixture-target',
        'occurred_at': '2026-06-28T12:00:00+00:00',
        'digest': HEX_A,
        'payload_digest': HEX_B,
        'dedupe_key': 'fixture-source:evt-1',
        'cooldown_key': None,
    }


def _rule_set() -> dict:
    return {'id': 'fixture.triggers', 'version': '0.1', 'digest': HEX_C}


def _rule() -> dict:
    return {'id': 'fixture.degraded.inspect', 'digest': HEX_D}


def _admission(*, allowed: bool = True, outcome: str = 'allowed') -> dict:
    return {
        'request_digest': 'sha256:' + HEX_A,
        'admission_digest': 'sha256:' + HEX_B,
        'admission': {'allowed': allowed, 'outcome': outcome},
    }


def test_trigger_decision_binds_event_rule_admission_and_operation() -> None:
    artifact = build_trigger_decision(
        decision_id='trigger-1',
        decision='plan_operation',
        reason='matched:fixture.degraded.inspect',
        decided_at='2026-06-28T12:00:00+00:00',
        source='test',
        event=_event(),
        rule_set=_rule_set(),
        rule=_rule(),
        admission=_admission(),
        operation_id='op-1',
        domain_authority='runtime-fixture',
    )

    assert artifact['event']['digest'] == 'sha256:' + HEX_A
    assert artifact['operation_ref'] == {'operation_id': 'op-1'}
    assert artifact['authority'] == {
        'truth_layer': 'sclite',
        'planner': 'rexecop',
        'policy_authority': 'govengine',
        'domain_authority': 'runtime-fixture',
        'execution_authority': 'rexecop',
    }
    assert trigger_decision_digest(artifact).startswith('sha256:')
    assert trigger_decision_descriptor(artifact)['artifact_type'] == 'trigger_decision'


def test_record_only_trigger_decision_cannot_claim_operation() -> None:
    with pytest.raises(ValueError, match='cannot carry operation_ref'):
        build_trigger_decision(
            decision_id='trigger-1',
            decision='ignore',
            reason='no_matching_trigger_rule',
            decided_at='2026-06-28T12:00:00+00:00',
            source='test',
            event=_event(),
            rule_set=_rule_set(),
            rule=None,
            admission=_admission(allowed=True, outcome='record_only'),
            operation_id='op-1',
            domain_authority='runtime-fixture',
        )


def test_plan_operation_requires_allowed_planning_admission() -> None:
    with pytest.raises(ValueError, match='requires allowed admission'):
        build_trigger_decision(
            decision_id='trigger-1',
            decision='plan_operation',
            reason='matched:fixture.degraded.inspect',
            decided_at='2026-06-28T12:00:00+00:00',
            source='test',
            event=_event(),
            rule_set=_rule_set(),
            rule=_rule(),
            admission=_admission(allowed=False, outcome='blocked'),
            operation_id='op-1',
            domain_authority='runtime-fixture',
        )


def test_trigger_decision_schema_rejects_raw_payload() -> None:
    artifact = build_trigger_decision(
        decision_id='trigger-1',
        decision='plan_operation',
        reason='matched:fixture.degraded.inspect',
        decided_at='2026-06-28T12:00:00+00:00',
        source='test',
        event=_event(),
        rule_set=_rule_set(),
        rule=_rule(),
        admission=_admission(),
        operation_id='op-1',
        domain_authority='runtime-fixture',
    )
    artifact['event']['payload'] = {'status': 'degraded'}

    with pytest.raises(JsonSchemaValidationError, match='unexpected fields'):
        validate_trigger_decision(artifact)
