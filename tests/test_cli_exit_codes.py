from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from sclite.integrity import artifact_descriptor

ROOT = Path(__file__).resolve().parents[1]
GOVENGINE_BUNDLE = ROOT / 'examples' / 'govengine-integration'
BAD_CROSS_HOST = ROOT / 'examples' / 'bad-review-bundle-cross-host'
SCOPED = ROOT / 'sclite' / 'examples' / 'scoped-ticket-v0.3'


def _run(args: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    run_env = dict(os.environ)
    if env:
        run_env.update(env)
    module = 'sclite.devtools' if args and args[0] == 'scope-fidelity' else 'sclite.kernel_cli'
    return subprocess.run([sys.executable, '-m', module, *args], cwd=str(ROOT), text=True, capture_output=True, check=False, env=run_env)


def _assert_clean_cli_failure(proc: subprocess.CompletedProcess[str], label: str, detail: str = 'invalid JSON') -> None:
    assert proc.returncode == 1
    assert label in proc.stderr
    assert detail in proc.stderr
    assert 'Traceback' not in proc.stderr


def _write_scoped_bundle(bundle: Path, *, target_in_scope: bool | None = True, validity: dict[str, str] | None = None) -> None:
    shutil.copytree(SCOPED, bundle)
    contract_path = bundle / 'execution_contract.json'
    ticket_path = bundle / 'execution_ticket.json'
    receipt_path = bundle / 'execution_receipt.json'
    evidence_path = bundle / 'evidence_contract.json'
    contract = json.loads(contract_path.read_text(encoding='utf-8'))
    ticket = json.loads(ticket_path.read_text(encoding='utf-8'))
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    evidence = json.loads(evidence_path.read_text(encoding='utf-8'))
    if target_in_scope is None:
        contract['target_binding'].pop('target_in_scope')
    else:
        contract['target_binding']['target_in_scope'] = target_in_scope
    if validity is not None:
        ticket['validity'] = validity

    contract_descriptor = artifact_descriptor(contract)
    ticket['links']['execution_contract']['descriptor'] = contract_descriptor
    ticket['integrity']['ticket_binds_execution_contract_digest'] = contract_descriptor['digest']
    ticket_descriptor = artifact_descriptor(ticket)
    receipt['links']['execution_contract']['descriptor'] = contract_descriptor
    receipt['links']['execution_ticket']['descriptor'] = ticket_descriptor
    receipt_descriptor = artifact_descriptor(receipt)
    evidence['links']['execution_ticket']['descriptor'] = ticket_descriptor
    evidence['links']['execution_receipt']['descriptor'] = receipt_descriptor
    for path, value in (
        (contract_path, contract),
        (ticket_path, ticket),
        (receipt_path, receipt),
        (evidence_path, evidence),
    ):
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


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


def test_packaged_lifecycle_example_selector() -> None:
    chain = _run(['validate-chain', '--example', 'contract-lifecycle-v0.2'])
    lifecycle = _run(['verify-lifecycle', '--example', 'contract-lifecycle-v0.2'])

    assert chain.returncode == 0, chain.stderr
    assert 'artifact_chain_ok:' in chain.stdout
    assert lifecycle.returncode == 0, lifecycle.stderr
    assert 'lifecycle_ok:' in lifecycle.stdout


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


@pytest.mark.parametrize('strict_jsonschema', [False, True])
def test_verify_ticket_use_cli_rejects_explicitly_false_scope(
    tmp_path: Path,
    strict_jsonschema: bool,
) -> None:
    bundle = tmp_path / 'scoped'
    _write_scoped_bundle(bundle, target_in_scope=False)
    args = [
        'verify-ticket-use',
        str(bundle / 'execution_ticket.json'),
        '--contract',
        str(bundle / 'execution_contract.json'),
        '--receipt',
        str(bundle / 'execution_receipt.json'),
        '--evidence-contract',
        str(bundle / 'evidence_contract.json'),
    ]
    if strict_jsonschema:
        args.append('--strict-jsonschema')

    proc = _run(args)

    assert proc.returncode == 1
    assert 'ticket_use_failed:execution_contract target_in_scope is explicitly false' in proc.stderr


@pytest.mark.parametrize('strict_jsonschema', [False, True])
def test_verify_ticket_use_cli_rejects_expired_window(
    tmp_path: Path,
    strict_jsonschema: bool,
) -> None:
    bundle = tmp_path / 'scoped'
    _write_scoped_bundle(
        bundle,
        validity={
            'not_before': '1970-01-01T00:00:00+00:00',
            'not_after': '1970-01-01T00:01:00+00:00',
        },
    )
    args = [
        'verify-ticket-use',
        str(bundle / 'execution_ticket.json'),
        '--contract',
        str(bundle / 'execution_contract.json'),
        '--receipt',
        str(bundle / 'execution_receipt.json'),
        '--evidence-contract',
        str(bundle / 'evidence_contract.json'),
    ]
    if strict_jsonschema:
        args.append('--strict-jsonschema')

    proc = _run(args)

    assert proc.returncode == 1
    assert 'ticket_use_failed:receipt execution interval is outside ticket validity window' in proc.stderr


@pytest.mark.parametrize('strict_jsonschema', [False, True])
def test_verify_ticket_use_cli_marks_unknown_scope_for_review(
    tmp_path: Path,
    strict_jsonschema: bool,
) -> None:
    bundle = tmp_path / 'scoped'
    _write_scoped_bundle(bundle, target_in_scope=None)
    args = [
        'verify-ticket-use',
        str(bundle / 'execution_ticket.json'),
        '--contract',
        str(bundle / 'execution_contract.json'),
        '--receipt',
        str(bundle / 'execution_receipt.json'),
        '--evidence-contract',
        str(bundle / 'evidence_contract.json'),
        '--format',
        'json',
    ]
    if strict_jsonschema:
        args.append('--strict-jsonschema')

    proc = _run(args)

    assert proc.returncode == 2
    assert json.loads(proc.stdout)['status'] == 'review'


@pytest.mark.parametrize('strict_jsonschema', [False, True])
def test_validate_ticket_cli_rejects_false_scope_and_reviews_unknown_scope(
    tmp_path: Path,
    strict_jsonschema: bool,
) -> None:
    false_bundle = tmp_path / 'false-scope'
    _write_scoped_bundle(false_bundle, target_in_scope=False)
    false_args = [
        'validate-ticket',
        str(false_bundle / 'execution_ticket.json'),
        '--contract',
        str(false_bundle / 'execution_contract.json'),
    ]
    if strict_jsonschema:
        false_args.append('--strict-jsonschema')

    false_proc = _run(false_args)

    assert false_proc.returncode == 1
    assert 'execution_ticket_failed:execution_contract target_in_scope is explicitly false' in false_proc.stderr

    unknown_bundle = tmp_path / 'unknown-scope'
    _write_scoped_bundle(unknown_bundle, target_in_scope=None)
    unknown_args = [
        'validate-ticket',
        str(unknown_bundle / 'execution_ticket.json'),
        '--contract',
        str(unknown_bundle / 'execution_contract.json'),
        '--format',
        'json',
    ]
    if strict_jsonschema:
        unknown_args.append('--strict-jsonschema')

    unknown_proc = _run(unknown_args)

    assert unknown_proc.returncode == 2
    assert json.loads(unknown_proc.stdout)['status'] == 'review'


def test_malformed_json_validate_artifact_fails_without_traceback(tmp_path: Path) -> None:
    bad = tmp_path / 'bad.json'
    bad.write_text('{', encoding='utf-8')

    proc = _run(['validate-artifact', '--schema', 'execution_contract.v0.2', str(bad)])

    _assert_clean_cli_failure(proc, 'security_contract_artifact_failed', 'input_validation_failed')


def test_validate_artifact_does_not_reflect_invalid_value(tmp_path: Path) -> None:
    bad = tmp_path / 'bad.json'
    bad.write_text('{"artifact_type":"SECRET_TOKEN_VALUE"}', encoding='utf-8')
    proc = _run(['validate-artifact', '--schema', 'redaction_policy.v0.2', str(bad)])
    assert proc.returncode == 1
    assert 'SECRET_TOKEN_VALUE' not in proc.stderr
    assert str(bad) not in proc.stderr


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
        env={'SCLITE_KERNEL_GUARD_KEY': 'test-key-that-is-at-least-32-bytes'},
    )

    _assert_clean_cli_failure(proc, 'secure_bundle_failed')


def test_malformed_json_inline_scope_plan_fails_without_traceback() -> None:
    proc = _run(['scope-fidelity', '--target', 'example.com', '--plan-step-json', '{'])

    _assert_clean_cli_failure(proc, 'scope_fidelity_failed')
