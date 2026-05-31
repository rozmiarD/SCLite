from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOVENGINE_BUNDLE = ROOT / 'examples' / 'govengine-integration'
BAD_CROSS_HOST = ROOT / 'examples' / 'bad-review-bundle-cross-host'
SCOPED = ROOT / 'sclite' / 'examples' / 'scoped-ticket-v0.3'


def _run(args: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    run_env = dict(os.environ)
    if env:
        run_env.update(env)
    return subprocess.run([sys.executable, '-m', 'sclite.cli', *args], cwd=str(ROOT), text=True, capture_output=True, check=False, env=run_env)


def _assert_clean_cli_failure(proc: subprocess.CompletedProcess[str], label: str) -> None:
    assert proc.returncode == 1
    assert label in proc.stderr
    assert 'invalid JSON' in proc.stderr
    assert 'Traceback' not in proc.stderr


def test_review_bundle_pass_exit_code_with_fail_on_review() -> None:
    proc = _run(['review', str(GOVENGINE_BUNDLE), '--format', 'json', '--fail-on', 'review'])
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)['verdict'] == 'pass'


def test_review_bundle_fail_verdict_exit_code_with_fail_on_review() -> None:
    proc = _run(['review', str(BAD_CROSS_HOST), '--format', 'json', '--fail-on', 'review'])
    assert proc.returncode == 2
    assert json.loads(proc.stdout)['verdict'] == 'fail'


def test_scope_fidelity_review_fail_on_review_exit_code() -> None:
    proc = _run(['scope-fidelity', '--target', 'opaque-target', '--fail-on', 'review'])
    assert proc.returncode == 2
    assert json.loads(proc.stdout)['verdict'] == 'review'


def test_tampered_chain_exit_code(tmp_path: Path) -> None:
    bundle = tmp_path / 'bundle'
    shutil.copytree(GOVENGINE_BUNDLE, bundle)
    manifest_path = bundle / 'artifact_chain_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['entries'][0]['descriptor']['digest'] = '0' * 64
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')

    proc = _run(['validate-chain', str(manifest_path)])
    assert proc.returncode == 1
    assert 'artifact_chain_failed' in proc.stderr


def test_invalid_review_bundle_exit_code(tmp_path: Path) -> None:
    bundle = tmp_path / 'bundle'
    shutil.copytree(GOVENGINE_BUNDLE, bundle)
    (bundle / '04_execution_ticket.json').unlink()

    proc = _run(['review', str(bundle), '--format', 'json'])
    assert proc.returncode == 1
    assert 'review_bundle_failed' in proc.stderr


def test_verify_ticket_use_overclaim_exit_code(tmp_path: Path) -> None:
    evidence = json.loads((SCOPED / 'evidence_contract.json').read_text(encoding='utf-8'))
    evidence['claims'][0]['requires_completed_execution'] = True
    evidence_path = tmp_path / 'evidence_contract.json'
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + '\n', encoding='utf-8')

    proc = _run([
        'verify-ticket-use',
        str(SCOPED / 'execution_ticket.json'),
        '--contract',
        str(SCOPED / 'execution_contract.json'),
        '--receipt',
        str(SCOPED / 'execution_receipt.json'),
        '--evidence-contract',
        str(evidence_path),
    ])
    assert proc.returncode == 1
    assert 'ticket_use_failed' in proc.stderr


def test_malformed_json_validate_artifact_fails_without_traceback(tmp_path: Path) -> None:
    bad = tmp_path / 'bad.json'
    bad.write_text('{', encoding='utf-8')

    proc = _run(['validate-artifact', '--schema', 'execution_contract.v0.2', str(bad)])

    _assert_clean_cli_failure(proc, 'security_contract_artifact_failed')


def test_malformed_json_validate_chain_fails_without_traceback(tmp_path: Path) -> None:
    bad = tmp_path / 'bad.json'
    bad.write_text('{', encoding='utf-8')

    proc = _run(['validate-chain', str(bad)])

    _assert_clean_cli_failure(proc, 'artifact_chain_failed')


def test_malformed_json_secure_bundle_fails_without_traceback(tmp_path: Path) -> None:
    bad = tmp_path / 'bad.json'
    bad.write_text('{', encoding='utf-8')

    proc = _run(
        ['verify-secure-bundle', str(bad), '--guard', str(bad)],
        env={'SCLITE_KERNEL_GUARD_KEY': 'test-key'},
    )

    _assert_clean_cli_failure(proc, 'secure_bundle_failed')


def test_malformed_json_inline_scope_plan_fails_without_traceback() -> None:
    proc = _run(['scope-fidelity', '--target', 'example.com', '--plan-step-json', '{'])

    _assert_clean_cli_failure(proc, 'scope_fidelity_failed')
