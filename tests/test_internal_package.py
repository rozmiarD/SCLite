from __future__ import annotations

import json
from pathlib import Path

import scl
from scl import artifacts
from scl.redaction import redact_prepared_spec
from scl.validation import validate_fixture_dir


PACKAGE_ROOT = Path(scl.__file__).resolve().parent
PACKAGE_FIXTURE_DIR = PACKAGE_ROOT / 'examples' / 'security-contract-proof'


def test_internal_scl_package_validates_clean_public_safe_fixture() -> None:
    assert validate_fixture_dir(PACKAGE_FIXTURE_DIR) == []


def test_internal_scl_package_validates_copied_schema_artifact() -> None:
    approved = json.loads((PACKAGE_FIXTURE_DIR / 'approved_execution_spec.json').read_text(encoding='utf-8'))
    artifacts.validate_artifact(approved, 'approved_execution_spec.v0.1')


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
