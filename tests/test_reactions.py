from __future__ import annotations

import json
from pathlib import Path

import pytest

from sclite import (
    ChainVerificationError,
    build_finding,
    build_observation_envelope,
    build_reaction_chain_manifest,
    build_reaction_plan,
    reaction_idempotency_key,
    validate_escalation_proposal,
    verify_reaction_chain_manifest,
)
from sclite.artifacts import JsonSchemaValidationError
from sclite.integrity import artifact_descriptor


PROFILE_REF = {'id': 'fixture-a', 'version': '1.0', 'digest': 'a' * 64}


def _artifacts() -> tuple[dict, dict, dict]:
    observation = build_observation_envelope(
        observation_id='obs-1',
        observed_at='2026-06-22T20:00:00+00:00',
        profile_ref=PROFILE_REF,
        operation_id='op-1',
        intent_id='inspect_state',
        target_id='target-a',
        facts={'state': {'status': 'degraded', 'count': 2}},
    )
    finding = build_finding(
        finding_id='finding-1',
        created_at='2026-06-22T20:00:01+00:00',
        profile_ref=PROFILE_REF,
        kind='fixture.degraded',
        severity='medium',
        summary='Fixture state is degraded.',
        observation=observation,
    )
    rule_digest = 'b' * 64
    plan = build_reaction_plan(
        reaction_id='reaction-1',
        created_at='2026-06-22T20:00:02+00:00',
        profile_ref=PROFILE_REF,
        rule_id='fixture.degraded.inspect',
        rule_digest=rule_digest,
        outcome='run_intent',
        intent_ref='inspect_state',
        child_operation_id='op-2',
        reason='matched fixture.degraded.inspect',
        depth=0,
        reaction_count=0,
        visited_rule_digests=[],
        idempotency_key=reaction_idempotency_key(
            profile_digest=PROFILE_REF['digest'],
            observation=observation,
            rule_digest=rule_digest,
            target_id='target-a',
        ),
        admission_status='admitted',
        admission_decision='allow',
        admission_decision_id='decision-1',
        observation=observation,
        finding=finding,
    )
    return observation, finding, plan


def _write_chain(root: Path, observation: dict, finding: dict, plan: dict) -> dict:
    manifest = build_reaction_chain_manifest(
        reaction_id='reaction-1',
        created_at='2026-06-22T20:00:02+00:00',
        observation=observation,
        finding=finding,
        reaction_plan=plan,
    )
    for name, value in (
        ('01_observation.json', observation),
        ('02_finding.json', finding),
        ('03_reaction_plan.json', plan),
    ):
        (root / name).write_text(json.dumps(value), encoding='utf-8')
    return manifest


def test_reaction_artifacts_are_content_bound_and_replayable(tmp_path: Path) -> None:
    observation, finding, plan = _artifacts()
    manifest = _write_chain(tmp_path, observation, finding, plan)

    result = verify_reaction_chain_manifest(manifest, root=tmp_path, strict_jsonschema=True)

    assert result['status'] == 'passed'
    assert result['reaction_semantics'] == 'passed'
    assert plan['links']['observation']['descriptor'] == artifact_descriptor(observation)


def test_reaction_replay_rejects_tampered_observation(tmp_path: Path) -> None:
    observation, finding, plan = _artifacts()
    manifest = _write_chain(tmp_path, observation, finding, plan)
    observation['facts']['state']['count'] = 3
    (tmp_path / '01_observation.json').write_text(json.dumps(observation), encoding='utf-8')

    with pytest.raises(ChainVerificationError, match='descriptor mismatch'):
        verify_reaction_chain_manifest(manifest, root=tmp_path)


def test_escalation_proposal_is_explicitly_untrusted_and_cannot_carry_command() -> None:
    proposal = {
        'artifact_type': 'escalation_proposal',
        'schema_version': 'v0.1',
        'schema_ref': 'schemas/escalation_proposal.v0.1.schema.json',
        'proposal_id': 'proposal-1',
        'reaction_id': 'reaction-1',
        'created_at': '2026-06-22T20:00:03+00:00',
        'suggested_outcome': 'run_intent',
        'intent_ref': 'inspect_state',
        'explanation': 'Re-check the bounded observation.',
        'evidence_refs': ['01_observation.json'],
        'authority': {
            'trusted': False,
            'may_execute': False,
            'requires_profile_validation': True,
            'requires_govengine_admission': True,
        },
    }
    validate_escalation_proposal(proposal)

    proposal['command'] = 'forbidden'
    with pytest.raises(JsonSchemaValidationError, match='unexpected fields'):
        validate_escalation_proposal(proposal)
