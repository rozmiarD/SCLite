from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from sclite import artifacts
from sclite.scope_fidelity import build_scope_fidelity_report, build_scope_fidelity_report_from_approved_spec, validate_scope_fidelity_report


PACKAGE_ROOT = Path(__import__('sclite').__file__).resolve().parent
APPROVED_FIXTURE = PACKAGE_ROOT / 'examples' / 'security-contract-proof' / 'approved_execution_spec.json'


def test_scope_fidelity_exact_host_binding_passes_schema() -> None:
    report = build_scope_fidelity_report(
        target='https://example.com',
        normalized_args=['https://example.com/login'],
        execution_plan=[{'tool': 'http_probe', 'args': ['https://example.com/login']}],
        target_in_scope=True,
        source_artifact='unit-test',
    )
    validate_scope_fidelity_report(report)
    assert report['artifact_type'] == 'scope_fidelity_report'
    assert report['verdict'] == 'pass'
    assert report['request_shape']['target_host_match_status'] == 'exact'
    assert report['request_shape']['request_shape_hygiene_status'] == 'clean'
    assert report['request_shape']['mismatched_hosts_detected'] == []
    assert report['public_safety']['live_target_execution'] is False


def test_scope_fidelity_cross_host_drift_fails() -> None:
    report = build_scope_fidelity_report(
        target='https://example.com',
        normalized_args=['https://evil.example.net'],
        execution_plan=[{'tool': 'http_probe', 'args': ['https://example.com']}],
        target_in_scope=True,
    )
    validate_scope_fidelity_report(report)
    assert report['verdict'] == 'fail'
    assert report['request_shape']['target_host_match_status'] == 'mixed'
    assert report['request_shape']['request_shape_hygiene_status'] == 'cross_host_mismatch'
    assert report['request_shape']['mismatched_hosts_detected'] == ['evil.example.net']


def test_scope_fidelity_missing_detected_hosts_requires_review() -> None:
    report = build_scope_fidelity_report(
        target='https://example.com',
        normalized_args=['--silent'],
        execution_plan=[{'tool': 'metadata_probe', 'args': ['--dry-run']}],
        target_in_scope=None,
    )
    validate_scope_fidelity_report(report)
    assert report['verdict'] == 'review'
    assert report['request_shape']['target_host_match_status'] == 'none_detected'
    assert report['request_shape']['request_shape_hygiene_status'] == 'ambiguous'


def test_scope_fidelity_from_approved_fixture() -> None:
    approved = json.loads(APPROVED_FIXTURE.read_text(encoding='utf-8'))
    report = build_scope_fidelity_report_from_approved_spec(approved, source_artifact='approved_fixture')
    validate_scope_fidelity_report(report)
    assert report['verdict'] == 'pass'
    assert report['target_host'] == 'example.com'


def test_scope_fidelity_schema_rejects_live_target_claim() -> None:
    report = build_scope_fidelity_report(target='https://example.com', normalized_args=['https://example.com'], execution_plan=[])
    report['public_safety']['live_target_execution'] = True
    try:
        validate_scope_fidelity_report(report)
    except artifacts.JsonSchemaValidationError as exc:
        assert 'live_target_execution' in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError('schema should reject live target execution claims')


def test_scope_fidelity_cli_fail_on_review_exit_code() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            '-m',
            'sclite.cli',
            'scope-fidelity',
            '--target',
            'https://example.com',
            '--normalized-arg',
            'metadata_probe',
            '--fail-on',
            'review',
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert '"verdict": "review"' in proc.stdout
