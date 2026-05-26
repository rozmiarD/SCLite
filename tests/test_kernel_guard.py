from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from sclite.artifacts import validate_artifact
from sclite.kernel_guard import (
    KERNEL_GUARD_SCHEMA_REF,
    KernelGuardError,
    build_kernel_guard_manifest,
    verify_kernel_guard_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'sclite' / 'examples' / 'contract-lifecycle-v0.2'
KEY = 'test-kernel-secret'
KEY_ID = 'test-key-20260525'


def _load_manifest() -> dict:
    value = json.loads((FIXTURE / 'artifact_chain_manifest.json').read_text(encoding='utf-8'))
    assert isinstance(value, dict)
    return value


def _guard(manifest: dict) -> dict:
    nonces = [f'nonce-{index}' for index, _entry in enumerate(manifest['entries'])]
    return build_kernel_guard_manifest(manifest, key=KEY, key_id=KEY_ID, nonces=nonces)


def test_kernel_guard_builds_schema_valid_sidecar_and_verifies() -> None:
    manifest = _load_manifest()
    guard = _guard(manifest)

    validate_artifact(guard, KERNEL_GUARD_SCHEMA_REF, root=ROOT)
    result = verify_kernel_guard_manifest(manifest, guard, key=KEY, root=FIXTURE, require_lifecycle=True)

    assert result['status'] == 'passed'
    assert result['entry_count'] == 6
    assert result['guard_profile'] == 'kernel_guard_hmac_v1'
    assert result['replay_status'] == 'not_checked'
    assert result['guard_root_tag'] == guard['root_tag']


def test_kernel_guard_rejects_manifest_metadata_spoofing() -> None:
    manifest = _load_manifest()
    guard = _guard(manifest)
    spoofed = copy.deepcopy(manifest)
    spoofed['signature_policy'] = {
        'mode': 'kernel_signed_claim_without_valid_guard',
        'identity_signature_required': True,
    }

    with pytest.raises(KernelGuardError, match='manifest_metadata_digest mismatch'):
        verify_kernel_guard_manifest(spoofed, guard, key=KEY, root=FIXTURE, require_lifecycle=True)


def test_kernel_guard_rejects_entry_tag_tampering() -> None:
    manifest = _load_manifest()
    guard = _guard(manifest)
    guard['entry_guards'][2]['tag'] = '0' * 64

    with pytest.raises(KernelGuardError, match=r'entry\[2\] tag mismatch'):
        verify_kernel_guard_manifest(manifest, guard, key=KEY, root=FIXTURE, require_lifecycle=True)


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
