from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import sclite
from sclite import artifacts
from sclite.redaction import build_default_redaction_policy, build_redaction_receipt, redact_prepared_spec
from sclite.bundles import review_bundle
from sclite.surfaces import build_public_snapshot_manifest, build_public_validation_surface_index
from sclite.validation import validate_fixture_dir


PACKAGE_ROOT = Path(sclite.__file__).resolve().parent
PACKAGE_FIXTURE_DIR = PACKAGE_ROOT / 'examples' / 'security-contract-proof'
PACKAGE_PREPARED_FIXTURE = PACKAGE_ROOT / 'examples' / 'prepared-execution-spec' / 'prepared_execution_spec.json'
PACKAGE_REDACTION_POLICY_FIXTURE = PACKAGE_ROOT / 'examples' / 'redaction-policy' / 'redaction_policy.json'
PACKAGE_REDACTION_RECEIPT_FIXTURE = PACKAGE_ROOT / 'examples' / 'redaction-receipt' / 'redaction_receipt.json'
PACKAGE_SURFACE_INDEX_FIXTURE = PACKAGE_ROOT / 'examples' / 'public-validation-surface-index' / 'public_validation_surface_index.json'
PACKAGE_SNAPSHOT_MANIFEST_FIXTURE = PACKAGE_ROOT / 'examples' / 'public-snapshot-manifest' / 'public_snapshot_manifest.json'
PACKAGE_REVIEW_RECORD_FIXTURE = PACKAGE_ROOT / 'examples' / 'lifecycle-review' / 'review_record.json'
PACKAGE_REVIEW_BUNDLE_DIR = PACKAGE_ROOT / 'examples' / 'review-bundle'


def test_internal_scl_package_validates_clean_public_safe_fixture() -> None:
    assert validate_fixture_dir(PACKAGE_FIXTURE_DIR) == []


def test_internal_scl_package_validates_copied_schema_artifact() -> None:
    approved = json.loads((PACKAGE_FIXTURE_DIR / 'approved_execution_spec.json').read_text(encoding='utf-8'))
    artifacts.validate_artifact(approved, 'approved_execution_spec.v0.1')


def test_strict_jsonschema_validation_accepts_public_safe_fixture() -> None:
    approved = json.loads((PACKAGE_FIXTURE_DIR / 'approved_execution_spec.json').read_text(encoding='utf-8'))
    artifacts.validate_artifact(approved, 'approved_execution_spec.v0.1', strict_jsonschema=True)


def test_strict_jsonschema_cli_accepts_public_safe_fixture() -> None:
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'sclite.cli',
            'validate-artifact',
            '--strict-jsonschema',
            '--schema',
            'approved_execution_spec.v0.1',
            str(PACKAGE_FIXTURE_DIR / 'approved_execution_spec.json'),
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert 'security_contract_artifact_ok' in result.stdout


def test_prepared_execution_spec_schema_validates_public_safe_fixture() -> None:
    prepared = json.loads(PACKAGE_PREPARED_FIXTURE.read_text(encoding='utf-8'))
    artifacts.validate_artifact(prepared, 'prepared_execution_spec.v0.1')
    assert prepared['artifact_type'] == 'prepared_execution_spec'
    assert prepared['resolved_tool'] == 'http_probe'


def test_redacted_prepared_execution_spec_schema_validates_public_safe_fixture() -> None:
    redacted = json.loads((PACKAGE_FIXTURE_DIR / 'prepared_execution_spec.redacted.json').read_text(encoding='utf-8'))
    artifacts.validate_artifact(redacted, 'redacted_prepared_execution_spec.v0.1')
    assert redacted['artifact_type'] == 'redacted_prepared_execution_spec'
    assert redacted['public_safety']['live_target_execution'] is False
    assert redacted['redaction']['credentials_included'] is False


def test_redacted_prepared_execution_spec_schema_rejects_raw_output_claim() -> None:
    redacted = json.loads((PACKAGE_FIXTURE_DIR / 'prepared_execution_spec.redacted.json').read_text(encoding='utf-8'))
    redacted['public_safety']['raw_stdout_stderr_included'] = True
    try:
        artifacts.validate_artifact(redacted, 'redacted_prepared_execution_spec.v0.1')
    except artifacts.JsonSchemaValidationError as exc:
        assert 'raw_stdout_stderr_included' in str(exc)
    else:  # pragma: no cover - assertion guard
        raise AssertionError('schema should reject public raw stdout/stderr claims')


def test_artifact_canonicalization_is_stable_for_key_order_and_unicode() -> None:
    first = {'b': ['żuraw', {'z': 1, 'a': True}], 'a': 'example'}
    second = {'a': 'example', 'b': ['żuraw', {'a': True, 'z': 1}]}
    assert artifacts.canonicalize_artifact(first) == artifacts.canonicalize_artifact(second)
    assert artifacts.artifact_sha256(first) == artifacts.artifact_sha256(second)
    descriptor = artifacts.build_artifact_hash(first)
    assert descriptor['canonicalization'] == 'sclite-json-v0.1'
    assert descriptor['algorithm'] == 'sha256'
    assert len(descriptor['digest']) == 64
    assert descriptor['canonical_bytes'] == len(artifacts.canonical_artifact_bytes(first))


def test_artifact_hash_changes_when_artifact_changes() -> None:
    base = {'artifact_type': 'example', 'value': 1}
    changed = {'artifact_type': 'example', 'value': 2}
    assert artifacts.artifact_sha256(base) != artifacts.artifact_sha256(changed)


def test_redaction_policy_and_receipt_schemas_validate_fixtures() -> None:
    policy = json.loads(PACKAGE_REDACTION_POLICY_FIXTURE.read_text(encoding='utf-8'))
    receipt = json.loads(PACKAGE_REDACTION_RECEIPT_FIXTURE.read_text(encoding='utf-8'))
    artifacts.validate_artifact(policy, 'redaction_policy.v0.1')
    artifacts.validate_artifact(receipt, 'redaction_receipt.v0.1')
    assert policy['public_safety']['credentials_included'] is False
    assert receipt['public_safety']['raw_source_included'] is False


def test_redaction_receipt_builder_records_hash_change_without_raw_source() -> None:
    source = {'artifact_type': 'example', 'token': 'synthetic-demo-token', 'stdout': 'synthetic output'}
    redacted = redact_prepared_spec(source)
    receipt = build_redaction_receipt(source, redacted, policy=build_default_redaction_policy(), generated_at='2026-05-05T21:30:00+00:00')
    artifacts.validate_artifact(receipt, 'redaction_receipt.v0.1')
    assert receipt['status'] == 'redacted'
    assert receipt['summary']['changed_paths_estimate'] >= 1
    assert 'synthetic-demo-token' not in json.dumps(receipt, sort_keys=True)


def test_public_surface_index_and_snapshot_manifest_schemas_validate_fixtures() -> None:
    index = json.loads(PACKAGE_SURFACE_INDEX_FIXTURE.read_text(encoding='utf-8'))
    manifest = json.loads(PACKAGE_SNAPSHOT_MANIFEST_FIXTURE.read_text(encoding='utf-8'))
    artifacts.validate_artifact(index, 'public_validation_surface_index.v0.1')
    artifacts.validate_artifact(manifest, 'public_snapshot_manifest.v0.1')
    assert index['summary']['surface_count'] >= 3
    assert manifest['summary']['hashed_file_count'] == manifest['summary']['file_count']


def test_review_record_schema_validates_packaged_fixture() -> None:
    record = json.loads(PACKAGE_REVIEW_RECORD_FIXTURE.read_text(encoding='utf-8'))
    artifacts.validate_artifact(record, 'review_record.v0.1')
    assert record['artifact_type'] == 'review_record'
    assert record['summary']['scope_fidelity_verdict'] == 'pass'


def test_packaged_review_bundle_can_be_reviewed() -> None:
    record = review_bundle(PACKAGE_REVIEW_BUNDLE_DIR)
    artifacts.validate_artifact(record, 'review_record.v0.1')
    assert record['review_profile'] == 'sclite-review-bundle-v0.1'


def test_surface_and_manifest_builders_return_schema_valid_artifacts() -> None:
    index = build_public_validation_surface_index(generated_at='2026-05-05T21:30:00+00:00')
    approved = json.loads((PACKAGE_FIXTURE_DIR / 'approved_execution_spec.json').read_text(encoding='utf-8'))
    manifest = build_public_snapshot_manifest([
        {'path': 'approved_execution_spec.json', 'artifact_type': 'approved_execution_spec', 'schema': 'approved_execution_spec.v0.1', 'public_safe': True, 'value': approved}
    ], generated_at='2026-05-05T21:30:00+00:00')
    artifacts.validate_artifact(index, 'public_validation_surface_index.v0.1')
    artifacts.validate_artifact(manifest, 'public_snapshot_manifest.v0.1')


def test_hash_artifact_cli_emits_same_digest_as_helper() -> None:
    approved_path = PACKAGE_FIXTURE_DIR / 'approved_execution_spec.json'
    approved = json.loads(approved_path.read_text(encoding='utf-8'))
    proc = subprocess.run(
        [
            sys.executable,
            '-m',
            'sclite.cli',
            'hash-artifact',
            '--schema',
            'approved_execution_spec.v0.1',
            '--format',
            'digest',
            str(approved_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.stdout.strip() == artifacts.artifact_sha256(approved)


def test_new_public_surface_clis_emit_schema_valid_json() -> None:
    policy_proc = subprocess.run([sys.executable, '-m', 'sclite.cli', 'redaction-policy'], capture_output=True, text=True, check=True)
    index_proc = subprocess.run([sys.executable, '-m', 'sclite.cli', 'validation-surface-index', '--generated-at', '2026-05-05T21:30:00+00:00'], capture_output=True, text=True, check=True)
    snapshot_proc = subprocess.run([
        sys.executable,
        '-m',
        'sclite.cli',
        'snapshot-manifest',
        '--file',
        str(PACKAGE_FIXTURE_DIR / 'approved_execution_spec.json'),
    ], capture_output=True, text=True, check=True)
    artifacts.validate_artifact(json.loads(policy_proc.stdout), 'redaction_policy.v0.1')
    artifacts.validate_artifact(json.loads(index_proc.stdout), 'public_validation_surface_index.v0.1')
    artifacts.validate_artifact(json.loads(snapshot_proc.stdout), 'public_snapshot_manifest.v0.1')


def test_fixture_is_synthetic_not_redacted_private_runtime_export() -> None:
    serialized = '\n'.join(path.read_text(encoding='utf-8') for path in sorted(PACKAGE_FIXTURE_DIR.iterdir()) if path.is_file())
    forbidden = [
        'session' + '=<redacted>',
        '<workspace' + '_path_redacted>',
        '<cookie' + '_redacted>',
        'operator' + '_supplied',
        'X-Bug' + '-Bounty',
        'X-Test' + '-Account-Email',
        'Author' + 'ization:',
        'Bearer' + ' ',
        str(Path.home()),
    ]
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
