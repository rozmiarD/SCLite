from __future__ import annotations

import pytest

from sclite import (
    ChainVerificationError,
    automation_chain_digest,
    automation_edge,
    automation_node,
    automation_owner_migration_contract,
    build_automation_chain,
    validate_automation_chain,
    verify_automation_chain,
)
from sclite.artifacts import JsonSchemaValidationError
from sclite.integrity import artifact_descriptor


PROFILE_REF = {'id': 'fixture-profile', 'version': '1.0', 'digest': 'a' * 64}
DECISION_DIGEST = 'b' * 64


def _artifact(artifact_type: str, schema_version: str, schema_ref: str, artifact_id: str) -> dict:
    return {
        'artifact_type': artifact_type,
        'schema_version': schema_version,
        'schema_ref': schema_ref,
        'artifact_id': artifact_id,
    }


def _ref(artifact_type: str, schema_version: str, schema_ref: str, artifact_id: str) -> dict:
    return artifact_descriptor(_artifact(artifact_type, schema_version, schema_ref, artifact_id))


def _chain() -> dict:
    nodes = [
        automation_node(
            node_id='op-source',
            node_type='operation',
            depth=0,
            status='completed',
            owner_layer='rexecop',
            authority_level='projection',
            operation_id='op-1',
            labels=('source',),
        ),
        automation_node(
            node_id='obs-1',
            node_type='observation',
            depth=0,
            status='completed',
            owner_layer='profile',
            authority_level='projection',
            artifact_ref=_ref(
                'observation_envelope',
                'v0.1',
                'schemas/observation_envelope.v0.1.schema.json',
                'obs-1',
            ),
        ),
        automation_node(
            node_id='finding-1',
            node_type='finding',
            depth=0,
            status='completed',
            owner_layer='profile',
            authority_level='projection',
            artifact_ref=_ref('finding', 'v0.1', 'schemas/finding.v0.1.schema.json', 'finding-1'),
        ),
        automation_node(
            node_id='reaction-1',
            node_type='reaction_plan',
            depth=0,
            status='admitted',
            owner_layer='rexecop',
            authority_level='projection',
            artifact_ref=_ref(
                'reaction_plan',
                'v0.1',
                'schemas/reaction_plan.v0.1.schema.json',
                'reaction-1',
            ),
        ),
        automation_node(
            node_id='op-child',
            node_type='child_operation',
            depth=1,
            status='planned',
            owner_layer='rexecop',
            authority_level='projection',
            operation_id='op-2',
        ),
        automation_node(
            node_id='receipt-child',
            node_type='execution_receipt',
            depth=1,
            status='completed',
            owner_layer='rexecop',
            authority_level='projection',
            artifact_ref=_ref(
                'execution_receipt',
                'v0.2',
                'schemas/execution_receipt.v0.2.schema.json',
                'receipt-1',
            ),
        ),
    ]
    edges = [
        automation_edge(
            edge_id='edge-observed',
            edge_type='observed',
            from_node='op-source',
            to_node='obs-1',
            depth=0,
        ),
        automation_edge(
            edge_id='edge-detected',
            edge_type='detected',
            from_node='obs-1',
            to_node='finding-1',
            depth=0,
        ),
        automation_edge(
            edge_id='edge-planned',
            edge_type='planned_reaction',
            from_node='finding-1',
            to_node='reaction-1',
            depth=0,
        ),
        automation_edge(
            edge_id='edge-admitted-child',
            edge_type='admitted_child',
            from_node='reaction-1',
            to_node='op-child',
            depth=1,
            idempotency_key='reaction-1:op-child',
            admission={
                'status': 'admitted',
                'decision_id': 'decision-1',
                'decision_digest': DECISION_DIGEST,
                'owner_layer': 'govengine',
            },
        ),
        automation_edge(
            edge_id='edge-receipt',
            edge_type='emitted_receipt',
            from_node='op-child',
            to_node='receipt-child',
            depth=1,
        ),
    ]
    return build_automation_chain(
        chain_id='automation:op-1',
        created_at='2026-07-05T12:00:00+00:00',
        profile_ref=PROFILE_REF,
        source_operation_id='op-1',
        nodes=nodes,
        edges=edges,
        controls={'max_depth': 2, 'max_nodes': 16, 'max_reactions': 4},
    )


def test_automation_chain_contract_verifies_multi_step_shape() -> None:
    chain = _chain()

    result = verify_automation_chain(chain, strict_jsonschema=True)

    assert result['status'] == 'passed'
    assert result['schema_ref'] == 'schemas/automation_chain.v0.1.schema.json'
    assert result['node_count'] == 6
    assert result['edge_count'] == 5
    assert result['reaction_count'] == 1
    assert result['child_edge_count'] == 1
    assert result['max_depth'] == 1
    assert result['root_chain_digest'] == automation_chain_digest(chain)
    assert result['verification_posture'] == 'automation_bridge_partial_v0.1'
    assert 'edge_endpoints_exist' in result['checked']
    assert 'graph_acyclicity' in result['not_checked']
    assert 'node_depth' in result['host_asserted']
    assert result['requires_external_verification']['graph_and_runtime_semantics'] == 'rexecop'
    assert result['requires_external_verification']['admission_authenticity_and_decision_binding'] == 'govengine'
    assert 'child_edge_governance_admission' not in result['invariants']


def test_automation_chain_rejects_duplicate_node_ids() -> None:
    chain = _chain()
    chain['nodes'].append(dict(chain['nodes'][0]))

    with pytest.raises(ChainVerificationError, match='duplicate automation node id'):
        validate_automation_chain(chain)


def test_automation_chain_rejects_unknown_edge_endpoint() -> None:
    chain = _chain()
    chain['edges'][0]['to_node'] = 'missing-node'

    with pytest.raises(ChainVerificationError, match='unknown to_node'):
        validate_automation_chain(chain)


def test_automation_chain_rejects_child_edge_without_idempotency() -> None:
    chain = _chain()
    chain['edges'][3]['idempotency_key'] = ''

    with pytest.raises(ChainVerificationError, match='missing idempotency_key'):
        validate_automation_chain(chain)


def test_automation_chain_treats_admission_owner_and_status_as_host_asserted() -> None:
    chain = _chain()
    chain['edges'][3]['admission']['owner_layer'] = 'rexecop'
    chain['edges'][3]['admission']['status'] = 'blocked'

    result = verify_automation_chain(chain)
    assert result['status'] == 'passed'
    assert 'admission_owner_layer' in result['host_asserted']
    assert 'admission_authenticity' in result['not_checked']


def test_automation_chain_rejects_depth_budget_drift() -> None:
    chain = _chain()
    chain['nodes'][4]['depth'] = 9

    with pytest.raises(ChainVerificationError, match='max_depth exceeded'):
        validate_automation_chain(chain)


def test_automation_chain_rejects_llm_authority() -> None:
    chain = _chain()
    chain['nodes'].append(
        automation_node(
            node_id='llm-1',
            node_type='escalation_proposal',
            depth=1,
            status='pending',
            owner_layer='llm',
            authority_level='projection',
        )
    )

    with pytest.raises(ChainVerificationError, match='llm automation nodes must be proposal-only'):
        validate_automation_chain(chain)


def test_automation_chain_schema_rejects_executable_llm_flag() -> None:
    chain = _chain()
    chain['controls']['llm_may_execute'] = True

    with pytest.raises(JsonSchemaValidationError, match='llm_may_execute'):
        validate_automation_chain(chain)


@pytest.mark.parametrize('mutation', ['cycle', 'self_loop', 'orphan', 'fake_depth'])
def test_automation_bridge_accepts_unverified_graph_semantics_without_claiming_them(
    mutation: str,
) -> None:
    chain = _chain()
    if mutation == 'cycle':
        chain['edges'].append(
            automation_edge(
                edge_id='cycle-edge',
                edge_type='continued_as',
                from_node='receipt-child',
                to_node='op-source',
                depth=1,
            )
        )
    elif mutation == 'self_loop':
        chain['edges'].append(
            automation_edge(
                edge_id='self-loop',
                edge_type='continued_as',
                from_node='obs-1',
                to_node='obs-1',
                depth=0,
            )
        )
    elif mutation == 'orphan':
        chain['nodes'].append(
            automation_node(
                node_id='orphan',
                node_type='external_ref',
                depth=0,
                status='pending',
                owner_layer='operator',
                authority_level='none',
            )
        )
    else:
        chain['nodes'][1]['depth'] = 2

    result = verify_automation_chain(chain)
    assert result['status'] == 'passed'
    assert 'graph_acyclicity' in result['not_checked']
    assert 'graph_connectivity' in result['not_checked']
    assert 'computed_depth' in result['not_checked']


def test_automation_owner_migration_contract_is_explicit() -> None:
    contract = automation_owner_migration_contract()
    assert contract['bridge_owner'] == 'sclite'
    assert 'dag_roots_connectivity' in contract['external_owners']['rexecop']
    assert 'admission_decision_binding' in contract['external_owners']['govengine']
