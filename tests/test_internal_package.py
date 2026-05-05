from __future__ import annotations

import json
from pathlib import Path

import sclite
from sclite import artifacts
from sclite.redaction import redact_prepared_spec
from sclite.validation import validate_fixture_dir


PACKAGE_ROOT = Path(sclite.__file__).resolve().parent
PACKAGE_FIXTURE_DIR = PACKAGE_ROOT / 'examples' / 'security-contract-proof'
PACKAGE_PREPARED_FIXTURE = PACKAGE_ROOT / 'examples' / 'prepared-execution-spec' / 'prepared_execution_spec.json'


def test_internal_scl_package_validates_clean_public_safe_fixture() -> None:
    assert validate_fixture_dir(PACKAGE_FIXTURE_DIR) == []


def test_internal_scl_package_validates_copied_schema_artifact() -> None:
    approved = json.loads((PACKAGE_FIXTURE_DIR / 'approved_execution_spec.json').read_text(encoding='utf-8'))
    artifacts.validate_artifact(approved, 'approved_execution_spec.v0.1')


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
