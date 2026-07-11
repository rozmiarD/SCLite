from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from sclite.artifacts import validate_artifact
from sclite.disclosure import (
    DISCLOSURE_STATUS_ORDER,
    DisclosureStatusError,
    build_disclosure_status,
    relative_public_path,
    validate_disclosure_transition,
)
from sclite.redaction import build_default_redaction_policy, build_redaction_receipt, sanitize_public_artifact
from sclite.surfaces import build_public_snapshot_manifest, build_public_validation_surface_index

ROOT = Path(__file__).resolve().parents[1]


def test_unknown_input_never_defaults_to_public_safe() -> None:
    manifest = build_public_snapshot_manifest([
        {'path': 'artifact.json', 'artifact_type': 'unknown', 'value': {'unknown_key': 'opaque'}}
    ], generated_at='2026-07-10T00:00:00+00:00')

    item = manifest['files'][0]
    assert item['disclosure']['status'] == 'unknown'
    assert item['disclosure']['checks'] == []
    assert 'public_safe' not in item
    validate_artifact(manifest, 'public_snapshot_manifest.v0.2', root=ROOT)


def test_removed_legacy_positive_boolean_is_ignored() -> None:
    manifest = build_public_snapshot_manifest([
        {'path': 'asserted.json', 'public_safe': True, 'value': {}}
    ])

    item = manifest['files'][0]
    assert item['disclosure']['status'] == 'unknown'
    assert 'public_safe' not in item


def test_externally_verified_claim_requires_policy_and_checks() -> None:
    manifest = build_public_snapshot_manifest([
        {
            'path': 'verified.json',
            'disclosure_status': 'externally_verified',
            'disclosure_policy': 'external-review-v1',
            'disclosure_checks': ['external_secret_scan', 'external_path_review'],
            'value': {},
        }
    ])

    item = manifest['files'][0]
    assert 'public_safe' not in item
    assert item['disclosure']['checks'] == ['external_secret_scan', 'external_path_review']
    assert item['disclosure']['publication_authorized'] is False


def test_disclosure_status_transitions_are_monotonic() -> None:
    for index, current in enumerate(DISCLOSURE_STATUS_ORDER):
        for proposed in DISCLOSURE_STATUS_ORDER[index:]:
            validate_disclosure_transition(current, proposed)
    with pytest.raises(DisclosureStatusError, match='downgrade'):
        validate_disclosure_transition('checks_performed', 'operator_asserted')


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        ('/home/alice/private/artifact.json', 'artifact.json'),
        (r'C:\\Users\\Alice\\private\\artifact.json', 'artifact.json'),
        ('../private/artifact.json', 'artifact.json'),
        ('nested/artifact.json', 'nested/artifact.json'),
    ],
)
def test_public_paths_hide_platform_topology(value: str, expected: str) -> None:
    assert relative_public_path(value) == expected


def test_arbitrary_snapshot_cli_file_is_unknown_and_relative(tmp_path: Path) -> None:
    artifact = tmp_path / 'opaque.json'
    artifact.write_text('{"unknown": "value"}\n', encoding='utf-8')
    result = subprocess.run(
        [sys.executable, '-m', 'sclite.devtools', 'snapshot-manifest', '--file', str(artifact)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout)

    assert payload['files'][0]['path'] == 'opaque.json'
    assert payload['files'][0]['disclosure']['status'] == 'unknown'
    assert 'public_safe' not in payload['files'][0]
    assert str(tmp_path) not in result.stdout


def test_heuristic_redaction_reports_coverage_without_negative_claims() -> None:
    source = {
        'token': 'synthetic-token',
        'mystery_credential_encoding': 'opaque-value',
        'path': r'C:\\Users\\Alice\\private.txt',
    }
    redacted = sanitize_public_artifact(source)
    policy = build_default_redaction_policy()
    receipt = build_redaction_receipt(source, redacted, policy=policy)

    assert receipt['disclosure']['status'] == 'checks_performed'
    assert receipt['disclosure']['coverage'] == {
        'credentials': 'heuristic_checked',
        'private_paths': 'heuristic_checked',
        'raw_output': 'heuristic_checked',
    }
    assert receipt['public_safety']['credentials_included'] == 'unknown'
    assert receipt['public_safety']['private_paths_included'] == 'unknown'
    assert redacted['mystery_credential_encoding'] == 'opaque-value'
    validate_artifact(policy, 'redaction_policy.v0.2', root=ROOT)
    validate_artifact(receipt, 'redaction_receipt.v0.2', root=ROOT)


def test_surface_index_contains_assertions_not_publication_claims() -> None:
    index = build_public_validation_surface_index()
    assert all(item['disclosure']['status'] == 'operator_asserted' for item in index['surfaces'])
    assert all('public_safe' not in item for item in index['surfaces'])
    assert index['disclosure']['publication_authorized'] is False
    validate_artifact(index, 'public_validation_surface_index.v0.2', root=ROOT)


def test_checks_performed_requires_evidence() -> None:
    with pytest.raises(DisclosureStatusError, match='requires concrete checks'):
        build_disclosure_status(status='checks_performed', policy='policy-v1')
