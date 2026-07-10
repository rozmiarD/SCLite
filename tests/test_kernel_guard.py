from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import sclite.kernel_guard as kernel_guard_module
from sclite.artifacts import validate_artifact
from sclite.kernel_guard import (
    KERNEL_GUARD_SCHEMA_REF,
    KernelGuardError,
    build_kernel_guard_manifest,
    verify_kernel_guard_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'sclite' / 'examples' / 'contract-lifecycle-v0.2'
GOLDEN = ROOT / 'tests' / 'golden' / 'kernel_guard_hmac_v1'
KEY = 'test-kernel-secret'
KEY_ID = 'test-key-20260525'


def _load_manifest() -> dict:
    value = json.loads((FIXTURE / 'artifact_chain_manifest.json').read_text(encoding='utf-8'))
    assert isinstance(value, dict)
    return value


def _guard(manifest: dict) -> dict:
    nonces = [f'nonce-{index}' for index, _entry in enumerate(manifest['entries'])]
    return build_kernel_guard_manifest(manifest, key=KEY, key_id=KEY_ID, nonces=nonces)


def _load_golden(name: str) -> dict | list:
    value = json.loads((GOLDEN / name).read_text(encoding='utf-8'))
    assert isinstance(value, (dict, list))
    return value


def test_kernel_guard_builds_schema_valid_sidecar_and_verifies() -> None:
    manifest = _load_manifest()
    guard = _guard(manifest)

    validate_artifact(guard, KERNEL_GUARD_SCHEMA_REF, root=ROOT)
    result = verify_kernel_guard_manifest(manifest, guard, key=KEY, root=FIXTURE, require_lifecycle=True)

    assert result['status'] == 'passed'
    assert result['chain_status'] == 'passed'
    assert result['lifecycle_status'] == 'passed'
    assert result['guard_status'] == 'passed'
    assert result['entry_count'] == 6
    assert result['guard_profile'] == 'kernel_guard_hmac_v1'
    assert result['replay_status'] == 'not_checked'
    assert result['guard_root_tag'] == guard['root_tag']


def test_kernel_guard_hmac_v1_golden_vector_freezes_transcript_and_tags() -> None:
    manifest = _load_golden('manifest.json')
    guard = _load_golden('kernel_guard_manifest.json')
    expected_entry_tags = _load_golden('expected_entry_tags.json')
    expected_root_tag = (GOLDEN / 'expected_root_tag.txt').read_text(encoding='utf-8').strip()
    key = (GOLDEN / 'key.txt').read_text(encoding='utf-8').strip()

    assert isinstance(manifest, dict)
    assert isinstance(guard, dict)
    assert isinstance(expected_entry_tags, list)

    nonces = [str(item['nonce']) for item in guard['entry_guards']]
    rebuilt = build_kernel_guard_manifest(
        manifest,
        key=key,
        key_id=str(guard['key_id']),
        nonces=nonces,
    )

    assert rebuilt == guard
    assert [
        {'seq': item['seq'], 'role': item['role'], 'tag': item['tag']}
        for item in rebuilt['entry_guards']
    ] == expected_entry_tags
    assert rebuilt['root_tag'] == expected_root_tag

    result = verify_kernel_guard_manifest(
        manifest,
        guard,
        key=key,
        root=FIXTURE,
        require_lifecycle=True,
    )

    assert result['status'] == 'passed'
    assert result['guard_status'] == 'passed'
    assert result['lifecycle_status'] == 'passed'
    assert result['guard_root_tag'] == expected_root_tag


def test_kernel_guard_rejects_manifest_metadata_spoofing() -> None:
    manifest = _load_manifest()
    guard = _guard(manifest)
    spoofed = copy.deepcopy(manifest)
    spoofed['signature_policy'] = {
        'mode': 'kernel_signed_claim_without_valid_guard',
        'identity_signature_required': True,
    }

    with pytest.raises(KernelGuardError, match='unsupported manifest signature_policy.mode'):
        verify_kernel_guard_manifest(spoofed, guard, key=KEY, root=FIXTURE, require_lifecycle=True)


@pytest.mark.parametrize(
    ('field', 'value', 'error'),
    [
        ('profile', 'forged-runtime-profile', 'unsupported manifest profile'),
        ('hash_algorithm', 'md5', 'manifest schema validation failed'),
    ],
)
def test_kernel_guard_builder_refuses_unverified_manifest_identity(
    field: str,
    value: str,
    error: str,
) -> None:
    manifest = _load_manifest()
    manifest[field] = value

    with pytest.raises(KernelGuardError, match=error):
        _guard(manifest)


def test_kernel_guard_rejects_entry_tag_tampering() -> None:
    manifest = _load_manifest()
    guard = _guard(manifest)
    guard['entry_guards'][2]['tag'] = '0' * 64

    with pytest.raises(KernelGuardError, match=r'entry\[2\] tag mismatch'):
        verify_kernel_guard_manifest(manifest, guard, key=KEY, root=FIXTURE, require_lifecycle=True)


def test_kernel_guard_enforces_key_id_even_without_sidecar_schema_validation() -> None:
    manifest = _load_manifest()
    guard = _guard(manifest)
    del guard['key_id']

    with pytest.raises(KernelGuardError, match='kernel guard missing key_id'):
        verify_kernel_guard_manifest(
            manifest,
            guard,
            key=KEY,
            root=FIXTURE,
            validate_guard_schema=False,
            require_lifecycle=True,
        )


def test_kernel_guard_uses_constant_time_compare_for_entry_and_root_tags(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _load_manifest()
    guard = _guard(manifest)
    real_compare_digest = kernel_guard_module.hmac.compare_digest
    calls: list[tuple[str, str]] = []

    def spy_compare_digest(left: str, right: str) -> bool:
        calls.append((left, right))
        return real_compare_digest(left, right)

    monkeypatch.setattr(kernel_guard_module.hmac, 'compare_digest', spy_compare_digest)

    result = verify_kernel_guard_manifest(manifest, guard, key=KEY, root=FIXTURE, require_lifecycle=True)

    assert result['status'] == 'passed'
    assert len(calls) == len(manifest['entries']) + 1
    assert calls[-1][0] == guard['root_tag']


def test_kernel_guard_validates_chain_before_tag_comparison(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = tmp_path / 'bundle'
    shutil.copytree(FIXTURE, bundle)
    manifest = json.loads((bundle / 'artifact_chain_manifest.json').read_text(encoding='utf-8'))
    guard = _guard(manifest)
    intent = json.loads((bundle / 'intent_contract.json').read_text(encoding='utf-8'))
    intent['intent']['summary'] = 'tampered before guard verification'
    (bundle / 'intent_contract.json').write_text(json.dumps(intent, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    calls: list[tuple[str, str]] = []

    def spy_compare_digest(left: str, right: str) -> bool:
        calls.append((left, right))
        return True

    monkeypatch.setattr(kernel_guard_module.hmac, 'compare_digest', spy_compare_digest)

    with pytest.raises(KernelGuardError, match='descriptor mismatch'):
        verify_kernel_guard_manifest(manifest, guard, key=KEY, root=bundle, require_lifecycle=True)
    assert calls == []


def test_kernel_guard_rejects_previous_tag_tampering() -> None:
    manifest = _load_manifest()
    guard = _guard(manifest)
    guard['entry_guards'][3]['previous_tag'] = '0' * 64

    with pytest.raises(KernelGuardError, match=r'entry\[3\] previous_tag mismatch'):
        verify_kernel_guard_manifest(manifest, guard, key=KEY, root=FIXTURE, require_lifecycle=True)


def test_kernel_guard_rejects_required_flag_tampering() -> None:
    manifest = _load_manifest()
    guard = _guard(manifest)
    tampered = copy.deepcopy(manifest)
    tampered['entries'][2]['required'] = False

    with pytest.raises(KernelGuardError, match=r'entry\[2\] required mismatch'):
        verify_kernel_guard_manifest(tampered, guard, key=KEY, root=FIXTURE, require_lifecycle=True)


def test_kernel_guard_rejects_sidecar_schema_drift() -> None:
    manifest = _load_manifest()
    guard = _guard(manifest)
    guard['entry_guards'][0]['unexpected'] = 'schema-drift'

    with pytest.raises(KernelGuardError, match='kernel guard schema validation failed'):
        verify_kernel_guard_manifest(manifest, guard, key=KEY, root=FIXTURE, require_lifecycle=True)


def test_kernel_guard_sidecar_schema_validation_is_independent_from_artifact_schema_validation() -> None:
    manifest = _load_manifest()
    guard = _guard(manifest)
    guard['entry_guards'][0]['unexpected'] = 'schema-drift'

    with pytest.raises(KernelGuardError, match='kernel guard schema validation failed'):
        verify_kernel_guard_manifest(
            manifest,
            guard,
            key=KEY,
            root=FIXTURE,
            validate_schemas=False,
            require_lifecycle=True,
        )


def test_kernel_guard_rejects_inserted_entry_with_old_guard() -> None:
    manifest = _load_manifest()
    guard = _guard(manifest)
    injected = copy.deepcopy(manifest)
    injected['entries'] = list(injected['entries'])
    injected['entries'].insert(4, copy.deepcopy(injected['entries'][4]))

    with pytest.raises(KernelGuardError, match='entry_count mismatch'):
        verify_kernel_guard_manifest(injected, guard, key=KEY, root=FIXTURE, validate_chain=False)


def test_verify_guarded_chain_cli(tmp_path: Path) -> None:
    manifest = _load_manifest()
    guard = _guard(manifest)
    guard_path = tmp_path / 'kernel_guard_manifest.json'
    guard_path.write_text(json.dumps(guard, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    env = dict(os.environ)
    env['SCLITE_KERNEL_GUARD_KEY'] = KEY
    proc = subprocess.run(
        [
            sys.executable,
            '-m',
            'sclite.cli',
            'verify-guarded-chain',
            str(FIXTURE / 'artifact_chain_manifest.json'),
            '--guard',
            str(guard_path),
            '--strict-lifecycle',
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        env=env,
        check=True,
    )

    assert proc.stdout.startswith('kernel_guard_ok:6:')


def test_verify_guarded_chain_cli_json_reports_layer_statuses(tmp_path: Path) -> None:
    manifest = _load_manifest()
    guard = _guard(manifest)
    guard_path = tmp_path / 'kernel_guard_manifest.json'
    guard_path.write_text(json.dumps(guard, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    env = dict(os.environ)
    env['SCLITE_KERNEL_GUARD_KEY'] = KEY
    proc = subprocess.run(
        [
            sys.executable,
            '-m',
            'sclite.cli',
            'verify-guarded-chain',
            str(FIXTURE / 'artifact_chain_manifest.json'),
            '--guard',
            str(guard_path),
            '--strict-lifecycle',
            '--format',
            'json',
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        env=env,
        check=True,
    )

    result = json.loads(proc.stdout)
    assert result['chain_status'] == 'passed'
    assert result['lifecycle_status'] == 'passed'
    assert result['guard_status'] == 'passed'
    assert result['replay_status'] == 'not_checked'


def test_verify_guarded_chain_cli_no_schema_still_validates_guard_sidecar_shape(tmp_path: Path) -> None:
    manifest = _load_manifest()
    guard = _guard(manifest)
    guard['entry_guards'][0]['unexpected'] = 'schema-drift'
    guard_path = tmp_path / 'kernel_guard_manifest.json'
    guard_path.write_text(json.dumps(guard, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    env = dict(os.environ)
    env['SCLITE_KERNEL_GUARD_KEY'] = KEY
    proc = subprocess.run(
        [
            sys.executable,
            '-m',
            'sclite.cli',
            'verify-guarded-chain',
            str(FIXTURE / 'artifact_chain_manifest.json'),
            '--guard',
            str(guard_path),
            '--no-schema',
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )

    assert proc.returncode == 1
    assert 'kernel_guard_failed:kernel guard schema validation failed' in proc.stderr
