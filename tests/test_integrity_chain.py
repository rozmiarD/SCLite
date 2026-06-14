from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from sclite.artifacts import validate_artifact
from sclite.integrity import (
    ChainVerificationError,
    artifact_descriptor,
    build_artifact_chain_manifest,
    verify_artifact_chain_manifest,
    verify_lifecycle_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'sclite' / 'examples' / 'contract-lifecycle-v0.2'
LIFECYCLE_FILES = [
    ('intent_contract', 'intent_contract.json'),
    ('policy_decision', 'policy_decision.json'),
    ('execution_contract', 'execution_contract.json'),
    ('execution_ticket', 'execution_ticket.json'),
    ('execution_receipt', 'execution_receipt.json'),
    ('evidence_contract', 'evidence_contract.json'),
]


def _load(name: str) -> dict:
    value = json.loads((FIXTURE / name).read_text(encoding='utf-8'))
    assert isinstance(value, dict)
    return value


def _manifest_for(artifacts: dict[str, dict]) -> dict:
    return build_artifact_chain_manifest(
        [
            {'role': role, 'path': path, 'value': artifacts[role]}
            for role, path in LIFECYCLE_FILES
        ],
        chain_id='sclite-v0.2-demo-lifecycle',
        created_at='2026-05-06T18:21:00+00:00',
    )


def _write_mutated_bundle(tmp_path: Path, artifacts: dict[str, dict]) -> Path:
    for role, path in LIFECYCLE_FILES:
        (tmp_path / path).write_text(json.dumps(artifacts[role], indent=2, sort_keys=True) + '\n', encoding='utf-8')
    manifest = _manifest_for(artifacts)
    manifest_path = tmp_path / 'artifact_chain_manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return manifest_path


def _artifacts() -> dict[str, dict]:
    return {role: copy.deepcopy(_load(path)) for role, path in LIFECYCLE_FILES}


def _write_lifecycle_files(tmp_path: Path, artifacts: dict[str, dict]) -> None:
    for role, path in LIFECYCLE_FILES:
        (tmp_path / path).write_text(json.dumps(artifacts[role], indent=2, sort_keys=True) + '\n', encoding='utf-8')


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
    assert result['chain_status'] == 'passed'
    assert result['lifecycle_status'] == 'not_checked'
    assert result['entry_count'] == 6
    assert result['checked_entries'][0] == 'intent_contract'
    assert result['checked_entries'][-1] == 'evidence_contract'
    assert result['semantic_checks'] == []


def test_v02_lifecycle_manifest_verifies_semantics_when_required() -> None:
    manifest = _load('artifact_chain_manifest.json')
    result = verify_artifact_chain_manifest(manifest, root=FIXTURE, require_lifecycle=True)

    assert result['chain_status'] == 'passed'
    assert result['lifecycle_status'] == 'passed'
    assert result['semantic_checks'] == [
        'role_order',
        'policy_binds_intent',
        'contract_binds_intent_and_policy',
        'ticket_binds_execution_contract',
        'receipt_binds_execution_ticket',
        'receipt_binds_execution_contract',
        'evidence_binds_execution_receipt',
        'evidence_binds_execution_ticket',
    ]


def test_verify_lifecycle_manifest_wrapper_is_fail_safe() -> None:
    manifest = _load('artifact_chain_manifest.json')
    result = verify_lifecycle_manifest(manifest, root=FIXTURE)

    assert result['status'] == 'passed'
    assert result['chain_status'] == 'passed'
    assert result['lifecycle_status'] == 'passed'
    assert 'ticket_binds_execution_contract' in result['semantic_checks']


def test_v02_chain_manifest_detects_digest_tampering() -> None:
    manifest = _load('artifact_chain_manifest.json')
    manifest['entries'][0]['descriptor']['digest'] = '0' * 64

    with pytest.raises(ChainVerificationError, match='descriptor mismatch'):
        verify_artifact_chain_manifest(manifest, root=FIXTURE)


def test_v02_lifecycle_detects_ticket_execution_contract_digest_mismatch(tmp_path: Path) -> None:
    artifacts = _artifacts()
    artifacts['execution_ticket']['integrity']['ticket_binds_execution_contract_digest'] = '0' * 64
    manifest_path = _write_mutated_bundle(tmp_path, artifacts)

    with pytest.raises(ChainVerificationError, match='ticket integrity execution_contract digest mismatch'):
        verify_artifact_chain_manifest(
            json.loads(manifest_path.read_text()),
            root=tmp_path,
            validate_schemas=False,
            require_lifecycle=True,
        )


def test_v02_lifecycle_rejects_policy_deny_with_executable_chain(tmp_path: Path) -> None:
    artifacts = _artifacts()
    artifacts['policy_decision']['decision'] = 'deny'
    artifacts['policy_decision']['reason_codes'] = ['policy_denied_fixture']
    manifest_path = _write_mutated_bundle(tmp_path, artifacts)

    with pytest.raises(ChainVerificationError, match='policy decision denies executable lifecycle'):
        verify_artifact_chain_manifest(
            json.loads(manifest_path.read_text()),
            root=tmp_path,
            validate_schemas=False,
            require_lifecycle=True,
        )


def test_v02_lifecycle_rejects_owner_approval_required_without_consumable_ticket(tmp_path: Path) -> None:
    artifacts = _artifacts()
    artifacts['policy_decision']['decision'] = 'owner_approval_required'
    artifacts['execution_ticket']['approval']['status'] = 'owner_approval_required'
    manifest_path = _write_mutated_bundle(tmp_path, artifacts)

    with pytest.raises(ChainVerificationError, match='owner approval required before executable lifecycle'):
        verify_artifact_chain_manifest(
            json.loads(manifest_path.read_text()),
            root=tmp_path,
            validate_schemas=False,
            require_lifecycle=True,
        )


@pytest.mark.parametrize('status', ('rejected', 'expired', 'revoked'))
def test_v02_lifecycle_rejects_terminal_ticket_approval_statuses(tmp_path: Path, status: str) -> None:
    artifacts = _artifacts()
    artifacts['execution_ticket']['approval']['status'] = status
    manifest_path = _write_mutated_bundle(tmp_path, artifacts)

    with pytest.raises(ChainVerificationError, match=f'execution ticket approval is terminal: {status}'):
        verify_artifact_chain_manifest(
            json.loads(manifest_path.read_text()),
            root=tmp_path,
            validate_schemas=False,
            require_lifecycle=True,
        )


def test_v02_lifecycle_rejects_missing_ticket_approval_status(tmp_path: Path) -> None:
    artifacts = _artifacts()
    del artifacts['execution_ticket']['approval']['status']
    manifest_path = _write_mutated_bundle(tmp_path, artifacts)

    with pytest.raises(ChainVerificationError, match='execution ticket is not approved for executable lifecycle: missing'):
        verify_artifact_chain_manifest(
            json.loads(manifest_path.read_text()),
            root=tmp_path,
            validate_schemas=False,
            require_lifecycle=True,
        )


def test_v02_lifecycle_detects_receipt_ticket_mismatch(tmp_path: Path) -> None:
    artifacts = _artifacts()
    artifacts['execution_receipt']['links']['execution_ticket']['descriptor']['digest'] = '0' * 64
    manifest_path = _write_mutated_bundle(tmp_path, artifacts)

    with pytest.raises(ChainVerificationError, match='receipt-ticket digest mismatch'):
        verify_artifact_chain_manifest(
            json.loads(manifest_path.read_text()),
            root=tmp_path,
            validate_schemas=False,
            require_lifecycle=True,
        )


def test_v02_lifecycle_detects_evidence_receipt_mismatch(tmp_path: Path) -> None:
    artifacts = _artifacts()
    artifacts['evidence_contract']['links']['execution_receipt']['descriptor']['digest'] = '0' * 64
    manifest_path = _write_mutated_bundle(tmp_path, artifacts)

    with pytest.raises(ChainVerificationError, match='evidence-receipt digest mismatch'):
        verify_artifact_chain_manifest(
            json.loads(manifest_path.read_text()),
            root=tmp_path,
            validate_schemas=False,
            require_lifecycle=True,
        )


def test_v02_lifecycle_detects_role_order_mismatch(tmp_path: Path) -> None:
    artifacts = _artifacts()
    reordered = [
        ('intent_contract', 'intent_contract.json'),
        ('policy_decision', 'policy_decision.json'),
        ('execution_ticket', 'execution_ticket.json'),
        ('execution_contract', 'execution_contract.json'),
        ('execution_receipt', 'execution_receipt.json'),
        ('evidence_contract', 'evidence_contract.json'),
    ]
    for role, path in LIFECYCLE_FILES:
        (tmp_path / path).write_text(json.dumps(artifacts[role], indent=2, sort_keys=True) + '\n', encoding='utf-8')
    manifest = build_artifact_chain_manifest(
        [{'role': role, 'path': path, 'value': artifacts[role]} for role, path in reordered],
        chain_id='sclite-v0.2-demo-lifecycle',
        created_at='2026-05-06T18:21:00+00:00',
    )

    with pytest.raises(ChainVerificationError, match='lifecycle roles mismatch'):
        verify_artifact_chain_manifest(manifest, root=tmp_path, validate_schemas=False, require_lifecycle=True)


def test_v02_lifecycle_strict_rejects_extra_role(tmp_path: Path) -> None:
    artifacts = _artifacts()
    _write_lifecycle_files(tmp_path, artifacts)
    (tmp_path / 'injected_extra_role.json').write_text(
        json.dumps(artifacts['execution_receipt'], indent=2, sort_keys=True) + '\n',
        encoding='utf-8',
    )
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
        chain_id='sclite-v0.2-demo-lifecycle',
        created_at='2026-05-06T18:21:00+00:00',
    )

    loose = verify_artifact_chain_manifest(manifest, root=tmp_path)
    assert loose['semantic_checks'] == []

    with pytest.raises(ChainVerificationError, match='lifecycle roles mismatch'):
        verify_artifact_chain_manifest(manifest, root=tmp_path, require_lifecycle=True)


def test_v02_lifecycle_strict_rejects_duplicate_role_without_overwrite(tmp_path: Path) -> None:
    artifacts = _artifacts()
    _write_lifecycle_files(tmp_path, artifacts)
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
        chain_id='sclite-v0.2-demo-lifecycle',
        created_at='2026-05-06T18:21:00+00:00',
    )

    loose = verify_artifact_chain_manifest(manifest, root=tmp_path)
    assert loose['checked_entries'].count('execution_contract') == 2
    assert loose['semantic_checks'] == []

    with pytest.raises(ChainVerificationError, match='lifecycle roles mismatch'):
        verify_artifact_chain_manifest(manifest, root=tmp_path, require_lifecycle=True)


def test_v02_lifecycle_detects_manifest_path_escape() -> None:
    manifest = _load('artifact_chain_manifest.json')
    manifest['entries'][0]['path'] = '../intent_contract.json'

    with pytest.raises(ChainVerificationError, match='path escapes root'):
        verify_artifact_chain_manifest(manifest, root=FIXTURE)


def test_v02_lifecycle_detects_symlink_manifest_path_escape(tmp_path: Path) -> None:
    root = tmp_path / 'bundle'
    root.mkdir()
    outside = tmp_path / 'outside_intent_contract.json'
    outside.write_text((FIXTURE / 'intent_contract.json').read_text(encoding='utf-8'), encoding='utf-8')
    link = root / 'linked_intent_contract.json'
    link.symlink_to(outside)
    manifest = _load('artifact_chain_manifest.json')
    manifest['entries'][0]['path'] = link.name

    with pytest.raises(ChainVerificationError, match='path escapes root'):
        verify_artifact_chain_manifest(manifest, root=root)


def test_validate_chain_cli() -> None:
    proc = subprocess.run(
        [sys.executable, '-m', 'sclite.cli', 'validate-chain', str(FIXTURE / 'artifact_chain_manifest.json')],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=True,
    )

    assert proc.stdout.startswith('artifact_chain_ok:6:')


def test_validate_chain_cli_json_keeps_lifecycle_semantics_loose() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            '-m',
            'sclite.cli',
            'validate-chain',
            str(FIXTURE / 'artifact_chain_manifest.json'),
            '--format',
            'json',
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=True,
    )

    result = json.loads(proc.stdout)
    assert result['chain_status'] == 'passed'
    assert result['lifecycle_status'] == 'not_checked'
    assert result['semantic_checks'] == []


def test_verify_lifecycle_cli_alias() -> None:
    proc = subprocess.run(
        [sys.executable, '-m', 'sclite.cli', 'verify-lifecycle', str(FIXTURE / 'artifact_chain_manifest.json')],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=True,
    )

    assert proc.stdout.startswith('lifecycle_ok:6:')


def test_verify_lifecycle_cli_json_reports_semantic_checks() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            '-m',
            'sclite.cli',
            'verify-lifecycle',
            str(FIXTURE / 'artifact_chain_manifest.json'),
            '--format',
            'json',
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=True,
    )

    result = json.loads(proc.stdout)
    assert result['chain_status'] == 'passed'
    assert result['lifecycle_status'] == 'passed'
    assert 'ticket_binds_execution_contract' in result['semantic_checks']
