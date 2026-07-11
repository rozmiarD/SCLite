from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import sclite
from sclite import artifacts
from sclite.bundles import review_bundle
from sclite.redaction import build_default_redaction_policy, build_redaction_receipt, redact_prepared_spec
from sclite.surfaces import build_public_snapshot_manifest, build_public_validation_surface_index


PACKAGE_ROOT = Path(sclite.__file__).resolve().parent
PACKAGE_REVIEW_BUNDLE_DIR = PACKAGE_ROOT / 'examples' / 'review-bundle'
PACKAGE_GOVENGINE_BUNDLE_DIR = PACKAGE_ROOT / 'examples' / 'govengine-integration'
PACKAGE_BAD_CROSS_HOST_BUNDLE_DIR = PACKAGE_ROOT / 'examples' / 'bad-review-bundle-cross-host'
PACKAGE_EXECUTION_CONTRACT = PACKAGE_REVIEW_BUNDLE_DIR / '03_execution_contract.json'
PACKAGE_REDACTION_POLICY_FIXTURE = PACKAGE_ROOT / 'examples' / 'redaction-policy' / 'redaction_policy.json'
PACKAGE_REDACTION_RECEIPT_FIXTURE = PACKAGE_ROOT / 'examples' / 'redaction-receipt' / 'redaction_receipt.json'
PACKAGE_SURFACE_INDEX_FIXTURE = PACKAGE_ROOT / 'examples' / 'public-validation-surface-index' / 'public_validation_surface_index.json'
PACKAGE_SNAPSHOT_MANIFEST_FIXTURE = PACKAGE_ROOT / 'examples' / 'public-snapshot-manifest' / 'public_snapshot_manifest.json'
PACKAGE_REVIEW_RECORD_FIXTURE = PACKAGE_ROOT / 'examples' / 'lifecycle-review' / 'review_record.json'


def test_packaged_current_lifecycle_artifacts_validate() -> None:
    schemas = {
        '01_intent_contract.json': 'intent_contract.v0.2',
        '02_policy_decision.json': 'policy_decision.v0.2',
        '03_execution_contract.json': 'execution_contract.v0.2',
        '04_execution_ticket.json': 'execution_ticket.v0.2',
        '05_execution_receipt.json': 'execution_receipt.v0.2',
        '06_evidence_contract.json': 'evidence_contract.v0.2',
        'artifact_chain_manifest.json': 'artifact_chain_manifest.v0.2',
    }
    for filename, schema in schemas.items():
        artifact = json.loads((PACKAGE_REVIEW_BUNDLE_DIR / filename).read_text(encoding='utf-8'))
        artifacts.validate_artifact(artifact, schema)


def test_packaged_govengine_fixture_current_contracts_validate() -> None:
    schemas = {
        '01_intent_contract.json': 'intent_contract.v0.2',
        '02_policy_decision.json': 'policy_decision.v0.2',
        '03_execution_contract.json': 'execution_contract.v0.2',
        '04_execution_ticket.json': 'execution_ticket.v0.3',
        '05_execution_receipt.json': 'execution_receipt.v0.2',
        '06_evidence_contract.json': 'evidence_contract.v0.2',
        'artifact_chain_manifest.json': 'artifact_chain_manifest.v0.2',
        'verification_receipt.json': 'review_record.v0.1',
        'trust_profile_ref.json': 'trust_profile_ref.v0.1',
        'carrier_profile_ref.json': 'carrier_profile_ref.v0.1',
    }
    for filename, schema in schemas.items():
        artifact = json.loads((PACKAGE_GOVENGINE_BUNDLE_DIR / filename).read_text(encoding='utf-8'))
        artifacts.validate_artifact(artifact, schema, strict_jsonschema=True)


def test_strict_jsonschema_validation_accepts_current_execution_contract() -> None:
    contract = json.loads(PACKAGE_EXECUTION_CONTRACT.read_text(encoding='utf-8'))
    artifacts.validate_artifact(contract, 'execution_contract.v0.2', strict_jsonschema=True)


def test_packaged_verification_result_schema_is_available() -> None:
    result = {
        'artifact_type': 'verification_result',
        'schema_version': 'v1',
        'schema_ref': 'schemas/verification_result.v1.schema.json',
        'profile': 'guarded-strict',
        'security_posture': 'guarded_domain_auth',
        'status': 'pass',
        'artifact_chain': 'pass',
        'strict_lifecycle': 'pass',
        'kernel_guard': 'pass',
        'replay': 'not_checked',
        'public_identity': 'not_claimed',
        'runtime_enforcement': 'not_claimed',
        'entry_count': 6,
        'checked_entries': ['intent_contract', 'policy_decision'],
        'root_chain_digest': 'a' * 64,
        'guard_profile': 'kernel_guard_hmac_v1',
        'guard_root_tag': 'b' * 64,
        'key_id': 'test-key',
    }
    artifacts.validate_artifact(result, 'verification_result.v1', strict_jsonschema=True)


def test_strict_jsonschema_cli_accepts_current_execution_contract() -> None:
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'sclite.kernel_cli',
            'validate-artifact',
            '--strict-jsonschema',
            '--schema',
            'execution_contract.v0.2',
            str(PACKAGE_EXECUTION_CONTRACT),
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert 'security_contract_artifact_ok' in result.stdout


def test_artifact_canonicalization_is_stable_for_key_order_and_unicode() -> None:
    first = {'b': ['zuraw', {'z': 1, 'a': True}], 'a': 'example'}
    second = {'a': 'example', 'b': ['zuraw', {'a': True, 'z': 1}]}
    assert artifacts.canonicalize_artifact(first) == artifacts.canonicalize_artifact(second)
    assert artifacts.artifact_sha256(first) == artifacts.artifact_sha256(second)
    descriptor = artifacts.build_artifact_hash(first)
    assert descriptor['canonicalization'] == 'sclite-json-v0.1'
    assert descriptor['algorithm'] == 'sha256'
    assert len(descriptor['digest']) == 64
    assert descriptor['canonical_bytes'] == len(artifacts.canonical_artifact_bytes(first))


def test_artifact_hash_changes_when_artifact_changes() -> None:
    assert artifacts.artifact_sha256({'value': 1}) != artifacts.artifact_sha256({'value': 2})


def test_redaction_policy_and_receipt_schemas_validate_fixtures() -> None:
    policy = json.loads(PACKAGE_REDACTION_POLICY_FIXTURE.read_text(encoding='utf-8'))
    receipt = json.loads(PACKAGE_REDACTION_RECEIPT_FIXTURE.read_text(encoding='utf-8'))
    artifacts.validate_artifact(policy, 'redaction_policy.v0.2')
    artifacts.validate_artifact(receipt, 'redaction_receipt.v0.2')
    assert policy['public_safety']['credentials_included'] == 'unknown'
    assert receipt['public_safety']['raw_source_included'] is False


def test_redaction_receipt_builder_records_hash_change_without_raw_source() -> None:
    source = {'artifact_type': 'example', 'token': 'synthetic-demo-token', 'stdout': 'synthetic output'}
    redacted = redact_prepared_spec(source)
    receipt = build_redaction_receipt(source, redacted, policy=build_default_redaction_policy(), generated_at='2026-05-05T21:30:00+00:00')
    artifacts.validate_artifact(receipt, 'redaction_receipt.v0.2')
    assert receipt['status'] == 'redacted'
    assert receipt['summary']['changed_paths_estimate'] >= 1
    assert 'synthetic-demo-token' not in json.dumps(receipt, sort_keys=True)


def test_public_surface_index_and_snapshot_manifest_schemas_validate_fixtures() -> None:
    index = json.loads(PACKAGE_SURFACE_INDEX_FIXTURE.read_text(encoding='utf-8'))
    manifest = json.loads(PACKAGE_SNAPSHOT_MANIFEST_FIXTURE.read_text(encoding='utf-8'))
    artifacts.validate_artifact(index, 'public_validation_surface_index.v0.2')
    artifacts.validate_artifact(manifest, 'public_snapshot_manifest.v0.2')
    assert index['summary']['surface_count'] >= 3
    assert manifest['summary']['hashed_file_count'] == manifest['summary']['file_count']


def test_review_record_schema_validates_packaged_fixture() -> None:
    record = json.loads(PACKAGE_REVIEW_RECORD_FIXTURE.read_text(encoding='utf-8'))
    artifacts.validate_artifact(record, 'review_record.v0.1')
    assert record['summary']['scope_fidelity_verdict'] == 'pass'


def test_packaged_review_bundles_remain_reviewable() -> None:
    assert review_bundle(PACKAGE_REVIEW_BUNDLE_DIR)['verdict'] in {'pass', 'review'}
    assert review_bundle(PACKAGE_GOVENGINE_BUNDLE_DIR)['verdict'] == 'pass'
    bad = review_bundle(PACKAGE_BAD_CROSS_HOST_BUNDLE_DIR)
    assert bad['verdict'] == 'fail'
    assert bad['summary']['scope_fidelity_verdict'] == 'fail'


def test_surface_and_manifest_builders_accept_current_artifact() -> None:
    index = build_public_validation_surface_index(generated_at='2026-05-05T21:30:00+00:00')
    contract = json.loads(PACKAGE_EXECUTION_CONTRACT.read_text(encoding='utf-8'))
    manifest = build_public_snapshot_manifest([
        {'path': '03_execution_contract.json', 'artifact_type': 'execution_contract', 'schema': 'execution_contract.v0.2', 'public_safe': True, 'value': contract}
    ], generated_at='2026-05-05T21:30:00+00:00')
    artifacts.validate_artifact(index, 'public_validation_surface_index.v0.2')
    artifacts.validate_artifact(manifest, 'public_snapshot_manifest.v0.2')


def test_hash_artifact_cli_emits_same_digest_as_helper() -> None:
    contract = json.loads(PACKAGE_EXECUTION_CONTRACT.read_text(encoding='utf-8'))
    proc = subprocess.run(
        [sys.executable, '-m', 'sclite.devtools', 'hash-artifact', '--schema', 'execution_contract.v0.2', '--format', 'digest', str(PACKAGE_EXECUTION_CONTRACT)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.stdout.strip() == artifacts.artifact_sha256(contract)


def test_public_surface_clis_emit_schema_valid_json() -> None:
    policy_proc = subprocess.run([sys.executable, '-m', 'sclite.devtools', 'redaction-policy'], capture_output=True, text=True, check=True)
    index_proc = subprocess.run([sys.executable, '-m', 'sclite.devtools', 'validation-surface-index', '--generated-at', '2026-05-05T21:30:00+00:00'], capture_output=True, text=True, check=True)
    snapshot_proc = subprocess.run([sys.executable, '-m', 'sclite.devtools', 'snapshot-manifest', '--file', str(PACKAGE_EXECUTION_CONTRACT)], capture_output=True, text=True, check=True)
    artifacts.validate_artifact(json.loads(policy_proc.stdout), 'redaction_policy.v0.2')
    artifacts.validate_artifact(json.loads(index_proc.stdout), 'public_validation_surface_index.v0.2')
    artifacts.validate_artifact(json.loads(snapshot_proc.stdout), 'public_snapshot_manifest.v0.2')


def test_current_fixture_is_synthetic_not_private_runtime_export() -> None:
    serialized = '\n'.join(path.read_text(encoding='utf-8') for path in sorted(PACKAGE_REVIEW_BUNDLE_DIR.iterdir()) if path.is_file())
    forbidden = ['session' + '=<redacted>', 'operator' + '_supplied', 'Author' + 'ization:', 'Bearer' + ' ', str(Path.home())]
    for needle in forbidden:
        assert needle not in serialized


def test_generic_redaction_helper_removes_public_unsafe_values() -> None:
    redacted = redact_prepared_spec({
        'path': str(Path.home() / 'private.txt'),
        'headers': [{'name': 'Author' + 'ization', 'value': 'Bearer' + ' secret', 'raw': 'Author' + 'ization: Bearer' + ' secret'}],
        'stdout': 'raw command output',
        'cookies': [{'name': 'session', 'value': 'abc'}],
    })
    text = json.dumps(redacted, sort_keys=True)
    assert str(Path.home()) not in text
    assert 'Bearer' + ' secret' not in text
    assert 'raw command output' not in text
    assert 'abc' not in text
    assert '<redacted>' in text
    assert '<local_path_omitted>' in text
