from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE = ROOT / 'sclite' / 'examples' / 'contract-lifecycle-v0.2'
GOVENGINE_BUNDLE = ROOT / 'examples' / 'govengine-integration'


def _run_json(args: list[str]) -> dict:
    proc = subprocess.run(
        [sys.executable, '-m', 'sclite.kernel_cli', *args],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    value = json.loads(proc.stdout)
    assert isinstance(value, dict)
    return value


def test_validate_chain_json_output_contract() -> None:
    result = _run_json(['validate-chain', str(LIFECYCLE / 'artifact_chain_manifest.json'), '--format', 'json'])

    assert result['status'] == 'passed'
    assert result['chain_status'] == 'passed'
    assert result['lifecycle_status'] == 'not_checked'
    assert result['verification_posture'] == 'integrity_only'
    assert result['semantic_checks'] == []
    assert result['lifecycle_role_summary']['status'] == 'canonical'


def test_verify_lifecycle_json_output_contract() -> None:
    result = _run_json(['verify-lifecycle', str(LIFECYCLE / 'artifact_chain_manifest.json'), '--format', 'json'])

    assert result['chain_status'] == 'passed'
    assert result['lifecycle_status'] == 'passed'
    assert result['verification_posture'] == 'strict_lifecycle'
    assert 'execution_ticket_schema_identity' in result['semantic_checks']
    assert 'ticket_binds_execution_contract' in result['semantic_checks']


def test_review_bundle_json_ticket_use_contract() -> None:
    result = _run_json(['review', str(GOVENGINE_BUNDLE), '--format', 'json', '--fail-on', 'review'])

    assert result['verdict'] == 'pass'
    assert result['summary']['ticket_use_status'] == 'pass'
    assert result['summary']['ticket_use_applicability'] == 'verified'
    checks = {check['name']: check for check in result['checks']}
    assert checks['ticket_use_profile']['status'] == 'pass'
