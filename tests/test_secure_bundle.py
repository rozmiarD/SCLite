from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from sclite.artifacts import validate_artifact
from sclite.integrity import build_artifact_chain_manifest
from sclite.kernel_guard import build_kernel_guard_manifest
from sclite.secure import SecureBundleError, verify_secure_bundle

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'sclite' / 'examples' / 'contract-lifecycle-v0.2'
GOVENGINE_BUNDLE = ROOT / 'examples' / 'govengine-integration'
KEY = 'test-kernel-secret'
KEY_ID = 'test-key-20260526'


def _load_manifest(base: Path) -> dict:
    value = json.loads((base / 'artifact_chain_manifest.json').read_text(encoding='utf-8'))
    assert isinstance(value, dict)
    return value


def _write_guard(base: Path, *, manifest: dict | None = None) -> Path:
    manifest = manifest or _load_manifest(base)
    guard = build_kernel_guard_manifest(
        manifest,
        key=KEY,
        key_id=KEY_ID,
        nonces=[f'nonce-{index}' for index, _entry in enumerate(manifest['entries'])],
    )
    guard_path = base / 'kernel_guard_manifest.json'
    guard_path.write_text(json.dumps(guard, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return guard_path


def _load_guard(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8'))
    assert isinstance(value, dict)
    return value


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def _run(args: list[str], *, env_key: bool = True) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    if env_key:
        env['SCLITE_KERNEL_GUARD_KEY'] = KEY
    else:
        env.pop('SCLITE_KERNEL_GUARD_KEY', None)
    return subprocess.run(
        [sys.executable, '-m', 'sclite.cli', *args],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def _copy_fixture(src: Path, dst: Path) -> Path:
    shutil.copytree(src, dst)
    return dst


def test_secure_bundle_profile_verifies_guarded_strict_manifest(tmp_path: Path) -> None:
    bundle = _copy_fixture(FIXTURE, tmp_path / 'bundle')
    guard_path = _write_guard(bundle)

    result = verify_secure_bundle(bundle / 'artifact_chain_manifest.json', guard_path=guard_path, key=KEY, root=bundle)

    assert result['status'] == 'passed'
    assert result['chain_status'] == 'passed'
    assert result['lifecycle_status'] == 'passed'
    assert result['guard_status'] == 'passed'
    assert result['secure_profile'] == 'guarded-strict'
    assert result['security_posture'] == 'guarded_domain_auth'
    assert result['replay_status'] == 'not_checked'
    assert result['fail_closed'] is True
    assert result['verification_result']['artifact_chain'] == 'pass'
    assert result['verification_result']['strict_lifecycle'] == 'pass'
    assert result['verification_result']['kernel_guard'] == 'pass'
    assert result['verification_result']['replay'] == 'not_checked'
    assert result['verification_result']['public_identity'] == 'not_claimed'
    assert result['verification_result']['runtime_enforcement'] == 'not_claimed'
    validate_artifact(result['verification_result'], 'verification_result.v1', root=ROOT)
    validate_artifact(result['verification_result'], 'verification_result.v1', root=ROOT, strict_jsonschema=True)


def test_secure_bundle_cli_accepts_review_bundle_directory_target(tmp_path: Path) -> None:
    bundle = _copy_fixture(GOVENGINE_BUNDLE, tmp_path / 'govengine-integration')
    _write_guard(bundle)
    proc = _run(['verify-secure-bundle', str(bundle)])

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith('secure_bundle_ok:6:')
    assert proc.stdout.strip().endswith(':replay_not_checked')


def test_secure_bundle_cli_json_includes_verification_result_contract(tmp_path: Path) -> None:
    bundle = _copy_fixture(GOVENGINE_BUNDLE, tmp_path / 'govengine-integration')
    _write_guard(bundle)
    proc = _run(['verify-secure-bundle', str(bundle), '--format', 'json'])

    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    verification_result = result['verification_result']
    assert result['chain_status'] == 'passed'
    assert result['lifecycle_status'] == 'passed'
    assert result['guard_status'] == 'passed'
    assert result['replay_status'] == 'not_checked'
    assert verification_result['artifact_type'] == 'verification_result'
    assert verification_result['schema_ref'] == 'schemas/verification_result.v1.schema.json'
    assert verification_result['artifact_chain'] == 'pass'
    assert verification_result['strict_lifecycle'] == 'pass'
    assert verification_result['kernel_guard'] == 'pass'
    assert verification_result['replay'] == 'not_checked'
    assert verification_result['public_identity'] == 'not_claimed'
    assert verification_result['runtime_enforcement'] == 'not_claimed'
    validate_artifact(verification_result, 'verification_result.v1', root=ROOT)


def test_secure_bundle_cli_no_schema_still_validates_guard_sidecar_shape(tmp_path: Path) -> None:
    bundle = _copy_fixture(GOVENGINE_BUNDLE, tmp_path / 'govengine-integration')
    guard_path = _write_guard(bundle)
    guard = _load_guard(guard_path)
    guard['entry_guards'][0]['unexpected'] = 'schema-drift'
    _write_json(guard_path, guard)

    proc = _run(['verify-secure-bundle', str(bundle), '--no-schema'])

    assert proc.returncode == 1
    assert 'secure_bundle_failed:kernel guard schema validation failed' in proc.stderr


def test_secure_bundle_without_guard_fails_closed() -> None:
    proc = _run(['verify-secure-bundle', str(GOVENGINE_BUNDLE)])

    assert proc.returncode == 1
    assert 'secure_bundle_failed:missing kernel guard sidecar' in proc.stderr


def test_validate_chain_require_guard_fails_on_missing_sidecar() -> None:
    proc = _run([
        'validate-chain',
        str(FIXTURE / 'artifact_chain_manifest.json'),
        '--strict-lifecycle',
        '--require-guard',
    ])

    assert proc.returncode == 1
    assert 'kernel_guard_failed:missing kernel guard sidecar' in proc.stderr


def test_review_require_guard_preflight_fails_on_unguarded_bundle() -> None:
    proc = _run(['review', str(GOVENGINE_BUNDLE), '--require-guard'])

    assert proc.returncode == 1
    assert 'review_bundle_failed:missing kernel guard sidecar' in proc.stderr


def test_secure_bundle_loose_lifecycle_fails(tmp_path: Path) -> None:
    artifacts = {
        'intent_contract': json.loads((FIXTURE / 'intent_contract.json').read_text(encoding='utf-8')),
        'policy_decision': json.loads((FIXTURE / 'policy_decision.json').read_text(encoding='utf-8')),
        'execution_contract': json.loads((FIXTURE / 'execution_contract.json').read_text(encoding='utf-8')),
        'execution_ticket': json.loads((FIXTURE / 'execution_ticket.json').read_text(encoding='utf-8')),
        'execution_receipt': json.loads((FIXTURE / 'execution_receipt.json').read_text(encoding='utf-8')),
        'evidence_contract': json.loads((FIXTURE / 'evidence_contract.json').read_text(encoding='utf-8')),
    }
    for filename in [
        'intent_contract.json',
        'policy_decision.json',
        'execution_contract.json',
        'execution_ticket.json',
        'execution_receipt.json',
        'evidence_contract.json',
    ]:
        (tmp_path / filename).write_text((FIXTURE / filename).read_text(encoding='utf-8'), encoding='utf-8')
    reordered = [
        ('intent_contract', 'intent_contract.json', artifacts['intent_contract']),
        ('policy_decision', 'policy_decision.json', artifacts['policy_decision']),
        ('execution_ticket', 'execution_ticket.json', artifacts['execution_ticket']),
        ('execution_contract', 'execution_contract.json', artifacts['execution_contract']),
        ('execution_receipt', 'execution_receipt.json', artifacts['execution_receipt']),
        ('evidence_contract', 'evidence_contract.json', artifacts['evidence_contract']),
    ]
    manifest = build_artifact_chain_manifest(
        [{'role': role, 'path': path, 'value': value} for role, path, value in reordered],
        chain_id='loose-lifecycle-test',
    )
    (tmp_path / 'artifact_chain_manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    guard_path = _write_guard(tmp_path, manifest=manifest)

    with pytest.raises(SecureBundleError, match='lifecycle roles mismatch'):
        verify_secure_bundle(tmp_path, guard_path=guard_path, key=KEY)


def test_secure_bundle_extra_role_fails_guarded_strict(tmp_path: Path) -> None:
    bundle = tmp_path / 'bundle'
    bundle.mkdir()
    artifacts = {
        'intent_contract': json.loads((FIXTURE / 'intent_contract.json').read_text(encoding='utf-8')),
        'policy_decision': json.loads((FIXTURE / 'policy_decision.json').read_text(encoding='utf-8')),
        'execution_contract': json.loads((FIXTURE / 'execution_contract.json').read_text(encoding='utf-8')),
        'execution_ticket': json.loads((FIXTURE / 'execution_ticket.json').read_text(encoding='utf-8')),
        'execution_receipt': json.loads((FIXTURE / 'execution_receipt.json').read_text(encoding='utf-8')),
        'evidence_contract': json.loads((FIXTURE / 'evidence_contract.json').read_text(encoding='utf-8')),
    }
    for filename in [
        'intent_contract.json',
        'policy_decision.json',
        'execution_contract.json',
        'execution_ticket.json',
        'execution_receipt.json',
        'evidence_contract.json',
    ]:
        (bundle / filename).write_text((FIXTURE / filename).read_text(encoding='utf-8'), encoding='utf-8')
    _write_json(bundle / 'injected_extra_role.json', artifacts['execution_receipt'])
    entries = [
        ('intent_contract', 'intent_contract.json', artifacts['intent_contract']),
        ('policy_decision', 'policy_decision.json', artifacts['policy_decision']),
        ('execution_contract', 'execution_contract.json', artifacts['execution_contract']),
        ('execution_ticket', 'execution_ticket.json', artifacts['execution_ticket']),
        ('injected_extra_role', 'injected_extra_role.json', artifacts['execution_receipt']),
        ('execution_receipt', 'execution_receipt.json', artifacts['execution_receipt']),
        ('evidence_contract', 'evidence_contract.json', artifacts['evidence_contract']),
    ]
    manifest = build_artifact_chain_manifest(
        [{'role': role, 'path': path, 'value': value} for role, path, value in entries],
        chain_id='extra-role-guarded-strict-test',
    )
    _write_json(bundle / 'artifact_chain_manifest.json', manifest)
    guard_path = _write_guard(bundle, manifest=manifest)

    with pytest.raises(SecureBundleError, match='lifecycle roles mismatch'):
        verify_secure_bundle(bundle, guard_path=guard_path, key=KEY)


def test_secure_bundle_duplicate_role_fails_guarded_strict(tmp_path: Path) -> None:
    bundle = tmp_path / 'bundle'
    bundle.mkdir()
    artifacts = {
        'intent_contract': json.loads((FIXTURE / 'intent_contract.json').read_text(encoding='utf-8')),
        'policy_decision': json.loads((FIXTURE / 'policy_decision.json').read_text(encoding='utf-8')),
        'execution_contract': json.loads((FIXTURE / 'execution_contract.json').read_text(encoding='utf-8')),
        'execution_ticket': json.loads((FIXTURE / 'execution_ticket.json').read_text(encoding='utf-8')),
        'execution_receipt': json.loads((FIXTURE / 'execution_receipt.json').read_text(encoding='utf-8')),
        'evidence_contract': json.loads((FIXTURE / 'evidence_contract.json').read_text(encoding='utf-8')),
    }
    for filename in [
        'intent_contract.json',
        'policy_decision.json',
        'execution_contract.json',
        'execution_ticket.json',
        'execution_receipt.json',
        'evidence_contract.json',
    ]:
        (bundle / filename).write_text((FIXTURE / filename).read_text(encoding='utf-8'), encoding='utf-8')
    entries = [
        ('intent_contract', 'intent_contract.json', artifacts['intent_contract']),
        ('policy_decision', 'policy_decision.json', artifacts['policy_decision']),
        ('execution_contract', 'execution_contract.json', artifacts['execution_contract']),
        ('execution_ticket', 'execution_ticket.json', artifacts['execution_ticket']),
        ('execution_contract', 'execution_contract.json', artifacts['execution_contract']),
        ('execution_receipt', 'execution_receipt.json', artifacts['execution_receipt']),
        ('evidence_contract', 'evidence_contract.json', artifacts['evidence_contract']),
    ]
    manifest = build_artifact_chain_manifest(
        [{'role': role, 'path': path, 'value': value} for role, path, value in entries],
        chain_id='duplicate-role-guarded-strict-test',
    )
    _write_json(bundle / 'artifact_chain_manifest.json', manifest)
    guard_path = _write_guard(bundle, manifest=manifest)

    with pytest.raises(SecureBundleError, match='lifecycle roles mismatch'):
        verify_secure_bundle(bundle, guard_path=guard_path, key=KEY)


def test_secure_bundle_metadata_spoofing_fails(tmp_path: Path) -> None:
    bundle = _copy_fixture(FIXTURE, tmp_path / 'bundle')
    manifest = _load_manifest(bundle)
    guard_path = _write_guard(bundle, manifest=manifest)
    spoofed = copy.deepcopy(manifest)
    spoofed['profile'] = 'runtime-consumable-forged-profile'
    manifest_path = tmp_path / 'artifact_chain_manifest.json'
    manifest_path.write_text(json.dumps(spoofed, indent=2, sort_keys=True) + '\n', encoding='utf-8')

    with pytest.raises(SecureBundleError, match='manifest_metadata_digest mismatch'):
        verify_secure_bundle(manifest_path, guard_path=guard_path, key=KEY, root=bundle)


def test_secure_bundle_root_chain_digest_tampering_fails(tmp_path: Path) -> None:
    bundle = _copy_fixture(FIXTURE, tmp_path / 'bundle')
    manifest = _load_manifest(bundle)
    guard_path = _write_guard(bundle, manifest=manifest)
    tampered = copy.deepcopy(manifest)
    tampered['root_chain_digest'] = '0' * 64
    manifest_path = tmp_path / 'artifact_chain_manifest.json'
    _write_json(manifest_path, tampered)

    with pytest.raises(SecureBundleError, match='root_chain_digest mismatch'):
        verify_secure_bundle(manifest_path, guard_path=guard_path, key=KEY, root=bundle)


def test_secure_bundle_artifact_body_tampering_fails(tmp_path: Path) -> None:
    bundle = _copy_fixture(FIXTURE, tmp_path / 'bundle')
    guard_path = _write_guard(bundle)
    intent = json.loads((bundle / 'intent_contract.json').read_text(encoding='utf-8'))
    intent['intent']['summary'] = 'tampered after guard generation'
    _write_json(bundle / 'intent_contract.json', intent)

    with pytest.raises(SecureBundleError, match='descriptor mismatch'):
        verify_secure_bundle(bundle, guard_path=guard_path, key=KEY)


def test_secure_bundle_required_flag_tampering_fails(tmp_path: Path) -> None:
    bundle = _copy_fixture(FIXTURE, tmp_path / 'bundle')
    manifest = _load_manifest(bundle)
    guard_path = _write_guard(bundle, manifest=manifest)
    tampered = copy.deepcopy(manifest)
    tampered['entries'][3]['required'] = False
    manifest_path = tmp_path / 'artifact_chain_manifest.json'
    manifest_path.write_text(json.dumps(tampered, indent=2, sort_keys=True) + '\n', encoding='utf-8')

    with pytest.raises(SecureBundleError, match=r'entry\[3\] required mismatch'):
        verify_secure_bundle(manifest_path, guard_path=guard_path, key=KEY, root=bundle)


def test_secure_bundle_nonce_tampering_fails(tmp_path: Path) -> None:
    bundle = _copy_fixture(FIXTURE, tmp_path / 'bundle')
    guard_path = _write_guard(bundle)
    guard = _load_guard(guard_path)
    guard['entry_guards'][1]['nonce'] = 'tampered-nonce'
    _write_json(guard_path, guard)

    with pytest.raises(SecureBundleError, match=r'entry\[1\] tag mismatch'):
        verify_secure_bundle(bundle, guard_path=guard_path, key=KEY)


def test_secure_bundle_key_id_tampering_fails(tmp_path: Path) -> None:
    bundle = _copy_fixture(FIXTURE, tmp_path / 'bundle')
    guard_path = _write_guard(bundle)
    guard = _load_guard(guard_path)
    guard['key_id'] = 'tampered-key-id'
    _write_json(guard_path, guard)

    with pytest.raises(SecureBundleError, match=r'entry\[0\] key_id mismatch'):
        verify_secure_bundle(bundle, guard_path=guard_path, key=KEY)


def test_secure_bundle_wrong_key_fails(tmp_path: Path) -> None:
    bundle = _copy_fixture(FIXTURE, tmp_path / 'bundle')
    guard_path = _write_guard(bundle)

    with pytest.raises(SecureBundleError, match=r'entry\[0\] tag mismatch'):
        verify_secure_bundle(bundle, guard_path=guard_path, key='wrong-kernel-secret')


def test_secure_bundle_full_chain_forgery_with_old_guard_fails(tmp_path: Path) -> None:
    bundle = _copy_fixture(FIXTURE, tmp_path / 'bundle')
    original = _load_manifest(bundle)
    old_guard_path = _write_guard(bundle, manifest=original)
    forged = copy.deepcopy(original)
    forged['chain_id'] = 'forged-chain'
    forged['created_at'] = '2026-05-26T00:00:00+00:00'
    forged_path = tmp_path / 'artifact_chain_manifest.json'
    forged_path.write_text(json.dumps(forged, indent=2, sort_keys=True) + '\n', encoding='utf-8')

    with pytest.raises(SecureBundleError, match='chain_id mismatch|manifest_metadata_digest mismatch'):
        verify_secure_bundle(forged_path, guard_path=old_guard_path, key=KEY, root=bundle)
