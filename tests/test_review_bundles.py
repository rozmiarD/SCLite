from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from sclite.artifacts import validate_artifact
from sclite.bundles import ReviewBundleError, review_bundle, review_bundle_summary, validate_review_bundle_shape

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / 'examples' / 'review-bundle'
PACKAGE_BUNDLE = ROOT / 'sclite' / 'examples' / 'review-bundle'
LOCAL_ADMIN_CHANGE = ROOT / 'examples' / 'local-admin-change'
GOVENGINE_INTEGRATION = ROOT / 'examples' / 'govengine-integration'


def test_review_bundle_shape_validates_canonical_fixture() -> None:
    result = validate_review_bundle_shape(BUNDLE)
    assert result['status'] == 'passed'
    assert result['files']['intent_contract'] == '01_intent_contract.json'


def test_review_bundle_emits_review_record() -> None:
    record = review_bundle(BUNDLE, generated_at='2026-05-15T19:05:00+02:00')
    validate_artifact(record, 'review_record.v0.1', strict_jsonschema=True)
    assert record['artifact_type'] == 'review_record'
    assert record['review_profile'] == 'sclite-review-bundle-v0.1'
    assert record['summary']['review_bundle_shape'] == 'canonical-v0.1'
    assert record['verdict'] == 'review'
    assert review_bundle_summary(record).startswith('review_bundle:review:6:')


def test_packaged_review_bundle_fixture_matches_public_shape() -> None:
    record = review_bundle(PACKAGE_BUNDLE)
    assert record['summary']['artifact_count'] == 6
    assert record['summary']['scope_fidelity_verdict'] == 'pass'


def test_local_admin_change_fixture_is_second_public_safe_review_bundle() -> None:
    record = review_bundle(LOCAL_ADMIN_CHANGE)
    validate_artifact(record, 'review_record.v0.1', strict_jsonschema=True)

    assert record['verdict'] == 'pass'
    assert record['summary']['scope_fidelity_verdict'] == 'pass'
    assert record['summary']['target_hosts'] == ['local.fixture']
    serialized = json.dumps(record)
    assert 'does_not_execute_tools' in serialized
    assert '"live_target_execution": false' in serialized
    assert '"network_execution_performed": true' not in serialized


@pytest.mark.parametrize('bundle', [GOVENGINE_INTEGRATION, LOCAL_ADMIN_CHANGE])
def test_alpha_review_bundle_families_keep_review_record_and_cli_summary_aligned(bundle: Path) -> None:
    record = review_bundle(bundle, generated_at='2026-05-21T00:00:00+00:00')
    validate_artifact(record, 'review_record.v0.1', strict_jsonschema=True)

    summary = subprocess.run(
        [sys.executable, '-m', 'sclite.cli', 'review', str(bundle), '--format', 'summary', '--fail-on', 'review'],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )

    assert summary.returncode == 0, summary.stderr
    assert summary.stdout.strip() == review_bundle_summary(record)
    assert record['review_profile'] == 'sclite-review-bundle-v0.1'
    assert record['summary']['review_bundle_shape'] == 'canonical-v0.1'
    assert tuple(record['summary']['review_bundle_files']) == (
        'intent_contract',
        'policy_decision',
        'execution_contract',
        'execution_ticket',
        'execution_receipt',
        'evidence_contract',
        'review_markdown',
        'verification_receipt',
    )


def test_review_bundle_rejects_missing_required_file(tmp_path: Path) -> None:
    target = tmp_path / 'review-bundle'
    shutil.copytree(BUNDLE, target)
    (target / '04_execution_ticket.json').unlink()
    with pytest.raises(ReviewBundleError, match='missing review bundle files'):
        validate_review_bundle_shape(target)


@pytest.mark.parametrize('filename', ['REVIEW.md', 'verification_receipt.json'])
def test_review_bundle_rejects_missing_canonical_sidecar(tmp_path: Path, filename: str) -> None:
    target = tmp_path / 'review-bundle'
    shutil.copytree(BUNDLE, target)
    (target / filename).unlink()
    with pytest.raises(ReviewBundleError, match='missing review bundle files'):
        validate_review_bundle_shape(target)


def test_verification_receipt_fixture_is_schema_valid() -> None:
    record = json.loads((BUNDLE / 'verification_receipt.json').read_text(encoding='utf-8'))
    validate_artifact(record, 'review_record.v0.1')
    assert record['source_manifest'] == 'artifact_chain_manifest.json'


def test_generated_review_record_uses_relative_source_paths() -> None:
    record = review_bundle(BUNDLE)
    assert record['source_manifest'] == 'artifact_chain_manifest.json'
    assert record['scope_fidelity_report']['source_artifact'] == 'artifact_chain_manifest.json'
    assert str(ROOT) not in json.dumps(record)


def test_review_cli_json_and_summary() -> None:
    json_result = subprocess.run(
        [sys.executable, '-m', 'sclite.cli', 'review', str(BUNDLE), '--format', 'json'],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    assert json_result.returncode == 0, json_result.stderr
    assert json.loads(json_result.stdout)['artifact_type'] == 'review_record'

    summary_result = subprocess.run(
        [sys.executable, '-m', 'sclite.cli', 'review', str(BUNDLE), '--format', 'summary'],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    assert summary_result.returncode == 0, summary_result.stderr
    assert summary_result.stdout.startswith('review_bundle:review:6:')


def test_export_review_bundle_cli_markdown() -> None:
    result = subprocess.run(
        [sys.executable, '-m', 'sclite.cli', 'export-review-bundle', str(BUNDLE), '--format', 'markdown'],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert '# SCLite Review Record' in result.stdout
    assert 'does_not_execute_tools' in result.stdout


def test_export_review_bundle_cli_output_file(tmp_path: Path) -> None:
    output = tmp_path / 'REVIEW.generated.md'
    result = subprocess.run(
        [sys.executable, '-m', 'sclite.cli', 'export-review-bundle', str(BUNDLE), '--output', str(output)],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert output.read_text(encoding='utf-8').startswith('# SCLite Review Record')
