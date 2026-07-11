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


def _rebind_lifecycle_artifacts(artifacts: dict[str, dict]) -> None:
    intent = artifacts['intent_contract']
    policy = artifacts['policy_decision']
    contract = artifacts['execution_contract']
    ticket = artifacts['execution_ticket']
    receipt = artifacts['execution_receipt']
    evidence = artifacts['evidence_contract']

    intent_descriptor = artifact_descriptor(intent)
    policy['links']['intent']['descriptor'] = intent_descriptor
    policy_descriptor = artifact_descriptor(policy)
    contract['links']['intent']['descriptor'] = intent_descriptor
    contract['links']['policy_decision']['descriptor'] = policy_descriptor
    contract_descriptor = artifact_descriptor(contract)
    ticket['links']['intent']['descriptor'] = intent_descriptor
    ticket['links']['policy_decision']['descriptor'] = policy_descriptor
    ticket['links']['execution_contract']['descriptor'] = contract_descriptor
    ticket['integrity']['ticket_binds_execution_contract_digest'] = contract_descriptor['digest']
    ticket_descriptor = artifact_descriptor(ticket)
    receipt['links']['execution_contract']['descriptor'] = contract_descriptor
    receipt['links']['execution_ticket']['descriptor'] = ticket_descriptor
    receipt_descriptor = artifact_descriptor(receipt)
    evidence['links']['execution_ticket']['descriptor'] = ticket_descriptor
    evidence['links']['execution_receipt']['descriptor'] = receipt_descriptor


def _upgrade_scope_v03(artifacts: dict[str, dict]) -> None:
    policy = artifacts['policy_decision']
    contract = artifacts['execution_contract']
    policy['schema_version'] = 'v0.3'
    policy['schema_ref'] = 'schemas/policy_decision.v0.3.schema.json'
    contract['schema_version'] = 'v0.3'
    contract['schema_ref'] = 'schemas/execution_contract.v0.3.schema.json'
    target = {
        'target': contract['target_binding']['target'],
        'target_host': contract['target_binding']['target_host'],
    }
    decision = {
        'artifact_type': 'govengine_scope_decision',
        'schema_version': 'v0.1',
        'decision_ref': 'govengine-scope:fixture',
        'status': 'in_scope',
        'authority': 'govengine',
        'subject': {'operation_id': 'fixture-operation'},
        'target': target,
    }
    assertion = {
        'status': decision['status'],
        'authority': decision['authority'],
        'decision_ref': decision['decision_ref'],
        'decision_digest': 'sha256:' + artifact_descriptor(decision)['digest'],
        'subject': decision['subject'],
        'target': decision['target'],
    }
    policy['authority_decision'] = decision
    policy['scope_assertion'] = assertion
    contract['scope_assertion'] = copy.deepcopy(assertion)


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
    assert result['verification_posture'] == 'integrity_only'
    assert result['entry_count'] == 6
    assert result['checked_entries'][0] == 'intent_contract'
    assert result['checked_entries'][-1] == 'evidence_contract'
    assert result['semantic_checks'] == []
    assert result['lifecycle_role_summary']['status'] == 'canonical'


def test_v02_lifecycle_manifest_verifies_semantics_when_required() -> None:
    manifest = _load('artifact_chain_manifest.json')
    result = verify_artifact_chain_manifest(manifest, root=FIXTURE, require_lifecycle=True)

    assert result['chain_status'] == 'passed'
    assert result['lifecycle_status'] == 'passed'
    assert result['verification_posture'] == 'strict_lifecycle'
    assert result['semantic_checks'][:6] == [
        'intent_contract_schema_identity',
        'policy_decision_schema_identity',
        'execution_contract_schema_identity',
        'execution_ticket_schema_identity',
        'execution_receipt_schema_identity',
        'evidence_contract_schema_identity',
    ]
    assert result['semantic_checks'][6:] == [
        'role_order',
        'policy_binds_intent',
        'contract_binds_intent_and_policy',
        'ticket_binds_execution_contract',
        'receipt_binds_execution_ticket',
        'receipt_binds_execution_contract',
        'evidence_binds_execution_receipt',
        'evidence_binds_execution_ticket',
        'target_in_scope_legacy_assertion',
        'receipt_within_ticket_validity',
    ]


def test_strict_lifecycle_accepts_registered_rexecop_manifest_profile() -> None:
    manifest = _load('artifact_chain_manifest.json')
    manifest['profile'] = 'sclite-v0.5-rexecop-integrity'

    result = verify_artifact_chain_manifest(manifest, root=FIXTURE, require_lifecycle=True)

    assert result['lifecycle_status'] == 'passed'


def test_verify_lifecycle_manifest_wrapper_is_fail_safe() -> None:
    manifest = _load('artifact_chain_manifest.json')
    result = verify_lifecycle_manifest(manifest, root=FIXTURE)

    assert result['status'] == 'passed'
    assert result['chain_status'] == 'passed'
    assert result['lifecycle_status'] == 'passed'
    assert 'ticket_binds_execution_contract' in result['semantic_checks']


def test_v03_scope_assertion_is_bound_without_authentication_claim(tmp_path: Path) -> None:
    artifacts = _artifacts()
    _upgrade_scope_v03(artifacts)
    _rebind_lifecycle_artifacts(artifacts)
    manifest_path = _write_mutated_bundle(tmp_path, artifacts)

    result = verify_lifecycle_manifest(json.loads(manifest_path.read_text()), root=tmp_path)

    assert result['lifecycle_status'] == 'passed'
    assert result['scope_status'] == 'authority_artifact_bound'
    assert result['scope_authority_authenticated'] == 'not_checked'
    assert 'scope_authority_artifact_binding' in result['semantic_checks']


@pytest.mark.parametrize('drift', ['digest', 'policy_target', 'execution_target', 'assertion'])
def test_v03_scope_assertion_rejects_binding_drift(tmp_path: Path, drift: str) -> None:
    artifacts = _artifacts()
    _upgrade_scope_v03(artifacts)
    if drift == 'digest':
        artifacts['policy_decision']['scope_assertion']['decision_digest'] = 'sha256:' + '0' * 64
        artifacts['execution_contract']['scope_assertion']['decision_digest'] = 'sha256:' + '0' * 64
    elif drift == 'policy_target':
        artifacts['policy_decision']['scope']['target_host'] = 'other.example'
    elif drift == 'execution_target':
        artifacts['execution_contract']['target_binding']['target'] = 'other/target'
    else:
        artifacts['execution_contract']['scope_assertion']['decision_ref'] = 'govengine-scope:other'
    _rebind_lifecycle_artifacts(artifacts)
    manifest_path = _write_mutated_bundle(tmp_path, artifacts)

    with pytest.raises(ChainVerificationError, match='scope assertion'):
        verify_lifecycle_manifest(json.loads(manifest_path.read_text()), root=tmp_path)


@pytest.mark.parametrize('strict_jsonschema', [False, True])
def test_strict_lifecycle_rejects_explicitly_false_scope(
    tmp_path: Path,
    strict_jsonschema: bool,
) -> None:
    artifacts = _artifacts()
    artifacts['policy_decision']['scope']['target_in_scope'] = False
    _rebind_lifecycle_artifacts(artifacts)
    manifest_path = _write_mutated_bundle(tmp_path, artifacts)

    with pytest.raises(ChainVerificationError, match='lifecycle target_in_scope is explicitly false'):
        verify_artifact_chain_manifest(
            json.loads(manifest_path.read_text()),
            root=tmp_path,
            strict_jsonschema=strict_jsonschema,
            require_lifecycle=True,
        )


@pytest.mark.parametrize('strict_jsonschema', [False, True])
def test_strict_lifecycle_marks_unknown_scope_for_review(
    tmp_path: Path,
    strict_jsonschema: bool,
) -> None:
    artifacts = _artifacts()
    del artifacts['policy_decision']['scope']['target_in_scope']
    _rebind_lifecycle_artifacts(artifacts)
    manifest_path = _write_mutated_bundle(tmp_path, artifacts)

    result = verify_artifact_chain_manifest(
        json.loads(manifest_path.read_text()),
        root=tmp_path,
        strict_jsonschema=strict_jsonschema,
        require_lifecycle=True,
    )

    assert result['status'] == 'review'
    assert result['lifecycle_status'] == 'review'
    assert result['scope_status'] == 'not_checked'


@pytest.mark.parametrize('strict_jsonschema', [False, True])
def test_strict_lifecycle_rejects_receipt_outside_ticket_validity_window(
    tmp_path: Path,
    strict_jsonschema: bool,
) -> None:
    artifacts = _artifacts()
    artifacts['execution_ticket']['validity'] = {
        'not_before': '1970-01-01T00:00:00+00:00',
        'not_after': '1970-01-01T00:01:00+00:00',
    }
    _rebind_lifecycle_artifacts(artifacts)
    manifest_path = _write_mutated_bundle(tmp_path, artifacts)

    with pytest.raises(ChainVerificationError, match='outside ticket validity window'):
        verify_artifact_chain_manifest(
            json.loads(manifest_path.read_text()),
            root=tmp_path,
            strict_jsonschema=strict_jsonschema,
            require_lifecycle=True,
        )


@pytest.mark.parametrize('strict_jsonschema', [False, True])
def test_strict_lifecycle_marks_missing_receipt_timestamps_for_review(
    tmp_path: Path,
    strict_jsonschema: bool,
) -> None:
    artifacts = _artifacts()
    artifacts['execution_receipt']['execution'].pop('started_at')
    artifacts['execution_receipt']['execution'].pop('ended_at')
    _rebind_lifecycle_artifacts(artifacts)
    manifest_path = _write_mutated_bundle(tmp_path, artifacts)

    result = verify_artifact_chain_manifest(
        json.loads(manifest_path.read_text()),
        root=tmp_path,
        strict_jsonschema=strict_jsonschema,
        require_lifecycle=True,
    )

    assert result['status'] == 'review'
    assert result['ticket_validity_status'] == 'review'


def test_v02_chain_manifest_detects_digest_tampering() -> None:
    manifest = _load('artifact_chain_manifest.json')
    manifest['entries'][0]['descriptor']['digest'] = '0' * 64

    with pytest.raises(ChainVerificationError, match='descriptor mismatch'):
        verify_artifact_chain_manifest(manifest, root=FIXTURE)


@pytest.mark.parametrize(
    ('label', 'mutate', 'error'),
    [
        ('artifact_type', lambda value: value.__setitem__('artifact_type', 'forged_manifest'), 'manifest schema validation failed'),
        ('schema_version', lambda value: value.__setitem__('schema_version', 'v999'), 'manifest schema validation failed'),
        ('schema_ref', lambda value: value.__setitem__('schema_ref', 'schemas/intent_contract.v0.2.schema.json'), 'manifest schema validation failed'),
        ('profile', lambda value: value.__setitem__('profile', 'forged-runtime-profile'), 'unsupported manifest profile'),
        ('canonicalization', lambda value: value.__setitem__('canonicalization', 'none'), 'manifest schema validation failed'),
        ('hash_algorithm', lambda value: value.__setitem__('hash_algorithm', 'md5'), 'manifest schema validation failed'),
        (
            'signature_policy',
            lambda value: value.__setitem__('signature_policy', {
                'mode': 'signed_identity',
                'identity_signature_required': True,
                'note': 'no signature is verified by this profile',
            }),
            'unsupported manifest signature_policy.mode',
        ),
    ],
)
@pytest.mark.parametrize('strict_jsonschema', [False, True])
def test_manifest_identity_and_policy_spoofing_are_rejected_before_entries(
    label: str,
    mutate: object,
    error: str,
    strict_jsonschema: bool,
) -> None:
    manifest = _load('artifact_chain_manifest.json')
    assert callable(mutate), label
    mutate(manifest)

    with pytest.raises(ChainVerificationError, match=error):
        verify_artifact_chain_manifest(
            manifest,
            root=FIXTURE,
            strict_jsonschema=strict_jsonschema,
            require_lifecycle=True,
        )


@pytest.mark.parametrize('strict_jsonschema', [False, True])
def test_manifest_result_reports_executed_constants_and_keeps_v02_extensions_open(
    strict_jsonschema: bool,
) -> None:
    manifest = _load('artifact_chain_manifest.json')
    manifest['audit_unknown_extension'] = {'value': True}

    result = verify_artifact_chain_manifest(
        manifest,
        root=FIXTURE,
        strict_jsonschema=strict_jsonschema,
        require_lifecycle=True,
    )

    assert result['status'] == 'passed'
    assert result['canonicalization'] == 'sclite-artifact-chain-v0.2'
    assert result['hash_algorithm'] == 'sha256'


@pytest.mark.parametrize('strict_jsonschema', [False, True])
def test_manifest_spoofing_cli_fails_closed(tmp_path: Path, strict_jsonschema: bool) -> None:
    manifest = _load('artifact_chain_manifest.json')
    manifest['hash_algorithm'] = 'md5'
    manifest_path = tmp_path / 'artifact_chain_manifest.json'
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    args = [
        sys.executable,
        '-m',
        'sclite.kernel_cli',
        'validate-chain',
        str(manifest_path),
        '--root',
        str(FIXTURE),
        '--strict-lifecycle',
    ]
    if strict_jsonschema:
        args.append('--strict-jsonschema')

    proc = subprocess.run(
        args,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 1
    assert 'artifact_chain_failed:manifest schema validation failed' in proc.stderr


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
    assert loose['lifecycle_role_summary']['extra_roles'] == ['injected_extra_role']

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
    assert loose['lifecycle_role_summary']['duplicate_roles'] == ['execution_contract']

    with pytest.raises(ChainVerificationError, match='lifecycle roles mismatch'):
        verify_artifact_chain_manifest(manifest, root=tmp_path, require_lifecycle=True)


def test_strict_lifecycle_rejects_role_schema_identity_drift_without_changing_loose_mode(tmp_path: Path) -> None:
    artifacts = _artifacts()
    artifacts['execution_ticket']['schema_ref'] = 'schemas/execution_receipt.v0.2.schema.json'
    manifest_path = _write_mutated_bundle(tmp_path, artifacts)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))

    loose = verify_artifact_chain_manifest(manifest, root=tmp_path, validate_schemas=False)
    assert loose['chain_status'] == 'passed'
    assert loose['lifecycle_status'] == 'not_checked'

    with pytest.raises(ChainVerificationError, match='execution_ticket schema identity mismatch'):
        verify_artifact_chain_manifest(manifest, root=tmp_path, validate_schemas=False, require_lifecycle=True)


def test_strict_lifecycle_rejects_role_artifact_type_drift(tmp_path: Path) -> None:
    artifacts = _artifacts()
    artifacts['execution_receipt']['artifact_type'] = 'execution_ticket'
    manifest_path = _write_mutated_bundle(tmp_path, artifacts)

    with pytest.raises(ChainVerificationError, match='execution_receipt artifact_type mismatch'):
        verify_artifact_chain_manifest(
            json.loads(manifest_path.read_text()),
            root=tmp_path,
            validate_schemas=False,
            require_lifecycle=True,
        )


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
        [sys.executable, '-m', 'sclite.kernel_cli', 'validate-chain', str(FIXTURE / 'artifact_chain_manifest.json')],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=True,
    )

    assert proc.stdout.startswith('artifact_chain_ok:6:')
    assert ':posture=integrity_only:lifecycle_not_checked' in proc.stdout


def test_validate_chain_cli_json_keeps_lifecycle_semantics_loose() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            '-m',
            'sclite.kernel_cli',
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
    assert result['verification_posture'] == 'integrity_only'
    assert result['semantic_checks'] == []


def test_verify_lifecycle_cli_alias() -> None:
    proc = subprocess.run(
        [sys.executable, '-m', 'sclite.kernel_cli', 'verify-lifecycle', str(FIXTURE / 'artifact_chain_manifest.json')],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=True,
    )

    assert proc.stdout.startswith('lifecycle_ok:6:')
    assert ':posture=strict_lifecycle:lifecycle_passed' in proc.stdout


def test_verify_lifecycle_cli_json_reports_semantic_checks() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            '-m',
            'sclite.kernel_cli',
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


def test_validate_chain_cli_optional_size_guard_fails_closed() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            '-m',
            'sclite.kernel_cli',
            'validate-chain',
            str(FIXTURE / 'artifact_chain_manifest.json'),
            '--max-artifact-bytes',
            '1',
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 1
    assert 'max_bytes=1' in proc.stderr
