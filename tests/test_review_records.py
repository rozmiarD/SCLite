from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

from sclite.artifacts import validate_artifact
from sclite.review import build_review_record_from_manifest, review_record_markdown
from sclite.scope_fidelity import build_lifecycle_scope_fidelity_report, validate_lifecycle_scope_fidelity_report

ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE = ROOT / 'sclite' / 'examples' / 'contract-lifecycle-v0.2'
MANIFEST = LIFECYCLE / 'artifact_chain_manifest.json'


def _load(name: str) -> dict:
    value = json.loads((LIFECYCLE / name).read_text(encoding='utf-8'))
    assert isinstance(value, dict)
    return value


def _artifacts() -> dict[str, dict]:
    return {
        'intent_contract': _load('intent_contract.json'),
        'policy_decision': _load('policy_decision.json'),
        'execution_contract': _load('execution_contract.json'),
        'execution_ticket': _load('execution_ticket.json'),
        'execution_receipt': _load('execution_receipt.json'),
        'evidence_contract': _load('evidence_contract.json'),
    }


def test_lifecycle_scope_fidelity_v02_passes_for_fixture() -> None:
    report = build_lifecycle_scope_fidelity_report(_artifacts(), source_artifact='unit-test')
    validate_lifecycle_scope_fidelity_report(report, strict_jsonschema=True)
    validate_artifact(report, 'scope_fidelity_report.v0.2')
    assert report['schema_version'] == 'v0.2'
    assert report['verdict'] == 'pass'
    assert report['summary']['target_hosts'] == ['example.com']
    assert report['summary']['lifecycle_target_status'] == 'consistent'


def test_lifecycle_scope_fidelity_v02_fails_on_policy_target_drift() -> None:
    artifacts = _artifacts()
    artifacts['policy_decision'] = copy.deepcopy(artifacts['policy_decision'])
    artifacts['policy_decision']['scope']['target_host'] = 'evil.example.net'
    report = build_lifecycle_scope_fidelity_report(artifacts)
    validate_lifecycle_scope_fidelity_report(report)
    assert report['verdict'] == 'fail'
    assert report['summary']['lifecycle_target_status'] == 'cross_role_target_mismatch'
    assert sorted(report['summary']['mismatched_hosts_detected']) == ['evil.example.net', 'example.com']


def test_review_record_aggregates_lifecycle_checks() -> None:
    record = build_review_record_from_manifest(MANIFEST, generated_at='2026-05-15T19:00:00+02:00')
    validate_artifact(record, 'review_record.v0.1', strict_jsonschema=True)
    assert record['artifact_type'] == 'review_record'
    assert record['verdict'] == 'review'
    assert record['summary']['artifact_count'] == 6
    assert record['summary']['scope_fidelity_verdict'] == 'pass'
    statuses = {check['name']: check['status'] for check in record['checks']}
    assert statuses['schema_validation'] == 'pass'
    assert statuses['chain_integrity'] == 'pass'
    assert statuses['lifecycle_binding'] == 'pass'
    assert statuses['scope_fidelity'] == 'pass'
    assert statuses['ticket_use_profile'] == 'review'
    assert record['summary']['ticket_use_applicability'] == 'not_applicable'


def test_review_record_markdown_contains_non_claims() -> None:
    record = build_review_record_from_manifest(MANIFEST, generated_at='2026-05-15T19:00:00+02:00')
    text = review_record_markdown(record)
    assert 'does_not_execute_tools' in text
    assert 'verdict: `review`' in text


def test_review_lifecycle_cli_emits_review_record_json() -> None:
    result = subprocess.run(
        [sys.executable, '-m', 'sclite.cli', 'review-lifecycle', str(MANIFEST), '--format', 'json'],
        cwd=str(ROOT),
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload['artifact_type'] == 'review_record'
    assert payload['summary']['scope_fidelity_verdict'] == 'pass'


def test_review_lifecycle_cli_markdown() -> None:
    result = subprocess.run(
        [sys.executable, '-m', 'sclite.cli', 'review-lifecycle', str(MANIFEST), '--format', 'markdown'],
        cwd=str(ROOT),
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert '# SCLite Review Record' in result.stdout
