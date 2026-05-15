from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from sclite.bundles import review_bundle

ROOT = Path(__file__).resolve().parents[1]
GOVENGINE_BUNDLE = ROOT / 'examples' / 'govengine-integration'


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    assert isinstance(value, Mapping), label
    return value


def test_review_bundle_machine_readable_contract_shape() -> None:
    record = review_bundle(GOVENGINE_BUNDLE, generated_at='2026-05-15T22:00:00+00:00')

    assert record['artifact_type'] == 'review_record'
    assert record['schema_version'] == 'v0.1'
    assert record['verdict'] in {'pass', 'review', 'fail'}
    assert record['verdict'] == 'pass'

    summary = _mapping(record.get('summary'), 'summary')
    assert summary['artifact_count'] == 6
    assert isinstance(summary['root_chain_digest'], str)
    assert len(summary['root_chain_digest']) == 64
    assert summary['scope_fidelity_verdict'] in {'pass', 'review', 'fail'}
    assert summary['review_bundle_shape'] == 'canonical-v0.1'

    checks = record.get('checks')
    assert isinstance(checks, list)
    assert checks
    assert all(isinstance(check, Mapping) for check in checks)
    assert all({'name', 'status', 'detail'} <= set(check) for check in checks if isinstance(check, Mapping))

    non_claims = record.get('non_claims')
    assert isinstance(non_claims, list)
    assert 'does_not_execute_tools' in non_claims
