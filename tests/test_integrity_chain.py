from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from sclite.artifacts import validate_artifact
from sclite.integrity import ChainVerificationError, artifact_descriptor, verify_artifact_chain_manifest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'sclite' / 'examples' / 'contract-lifecycle-v0.2'


def _load(name: str) -> dict:
    value = json.loads((FIXTURE / name).read_text(encoding='utf-8'))
    assert isinstance(value, dict)
    return value


def test_v02_lifecycle_artifacts_validate_against_schemas() -> None:
    for name in [
        'intent_contract.json',
        'policy_decision.json',
        'execution_contract.json',
        'execution_ticket.json',
        'execution_receipt.json',
        'evidence_contract.json',
        'artifact_chain_manifest.json',
    ]:
        artifact = _load(name)
        validate_artifact(artifact, str(artifact['schema_ref']), root=ROOT)


def test_artifact_descriptor_is_canonical_and_stable() -> None:
    intent = _load('intent_contract.json')
    reordered = dict(reversed(list(intent.items())))

    assert artifact_descriptor(intent) == artifact_descriptor(reordered)
    assert artifact_descriptor(intent)['algorithm'] == 'sha256'


def test_v02_chain_manifest_verifies_fixture() -> None:
    manifest = _load('artifact_chain_manifest.json')
    result = verify_artifact_chain_manifest(manifest, root=FIXTURE)

    assert result['status'] == 'passed'
    assert result['entry_count'] == 6
    assert result['checked_entries'][0] == 'intent_contract'
    assert result['checked_entries'][-1] == 'evidence_contract'


def test_v02_chain_manifest_detects_digest_tampering() -> None:
    manifest = _load('artifact_chain_manifest.json')
    manifest['entries'][0]['descriptor']['digest'] = '0' * 64

    with pytest.raises(ChainVerificationError, match='descriptor mismatch'):
        verify_artifact_chain_manifest(manifest, root=FIXTURE)


def test_validate_chain_cli() -> None:
    proc = subprocess.run(
        [sys.executable, '-m', 'sclite.cli', 'validate-chain', str(FIXTURE / 'artifact_chain_manifest.json')],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=True,
    )

    assert proc.stdout.startswith('artifact_chain_ok:6:')
