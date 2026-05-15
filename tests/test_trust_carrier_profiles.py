from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from sclite.artifacts import validate_artifact
from sclite.profiles import (
    ProfileReferenceError,
    profile_ref_summary,
    validate_carrier_profile_ref,
    validate_trust_profile_ref,
)

ROOT = Path(__file__).resolve().parents[1]
SUBJECT_PATH = ROOT / 'sclite' / 'examples' / 'scoped-ticket-v0.3' / 'execution_ticket.json'
FIXTURE = ROOT / 'sclite' / 'examples' / 'trust-carrier-profiles'


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8'))
    assert isinstance(value, dict)
    return value


def _subject() -> dict:
    return _load(SUBJECT_PATH)


def _trust_ref() -> dict:
    return copy.deepcopy(_load(FIXTURE / 'trust_profile_ref.json'))


def _carrier_ref() -> dict:
    return copy.deepcopy(_load(FIXTURE / 'carrier_profile_ref.json'))


def test_trust_profile_ref_schema_validates_fixture() -> None:
    validate_artifact(_trust_ref(), 'trust_profile_ref.v0.1')
    validate_artifact(_trust_ref(), 'trust_profile_ref.v0.1', strict_jsonschema=True)


def test_carrier_profile_ref_schema_validates_fixture() -> None:
    validate_artifact(_carrier_ref(), 'carrier_profile_ref.v0.1')
    validate_artifact(_carrier_ref(), 'carrier_profile_ref.v0.1', strict_jsonschema=True)


def test_trust_profile_ref_validates_digest_binding() -> None:
    checks = validate_trust_profile_ref(_trust_ref(), _subject())
    assert 'trust_profile_subject_descriptor_bound' in checks
    assert 'trust_profile_subject_digest_bound' in checks


def test_carrier_profile_ref_validates_digest_binding() -> None:
    checks = validate_carrier_profile_ref(_carrier_ref(), _subject())
    assert 'carrier_profile_subject_descriptor_bound' in checks
    assert 'carrier_profile_subject_digest_bound' in checks


def test_profile_ref_summary_is_public_safe() -> None:
    summary = profile_ref_summary(_trust_ref())
    assert summary['profile'] == 'digest_only'
    assert summary['subject_artifact_digest']
    assert 'does_not_decide_trust' in summary['non_claims']


def test_trust_profile_ref_rejects_subject_digest_drift() -> None:
    ref = _trust_ref()
    ref['integrity']['subject_artifact_digest'] = '0' * 64
    with pytest.raises(ProfileReferenceError, match='subject_artifact_digest mismatch'):
        validate_trust_profile_ref(ref, _subject())


def test_carrier_profile_ref_rejects_subject_descriptor_drift() -> None:
    ref = _carrier_ref()
    ref['links']['subject']['descriptor']['digest'] = '0' * 64
    with pytest.raises(ProfileReferenceError, match='subject descriptor mismatch'):
        validate_carrier_profile_ref(ref, _subject())


def test_trust_profile_ref_rejects_unknown_profile() -> None:
    ref = _trust_ref()
    ref['trust_profile'] = 'inline_root_ca'
    with pytest.raises(Exception):
        validate_trust_profile_ref(ref, _subject())


def test_validate_trust_profile_cli() -> None:
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'sclite.cli',
            'validate-trust-profile',
            str(FIXTURE / 'trust_profile_ref.json'),
            '--subject',
            str(SUBJECT_PATH),
        ],
        cwd=str(ROOT),
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith('trust_profile_ref_ok:digest_only:')


def test_validate_carrier_profile_cli() -> None:
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'sclite.cli',
            'validate-carrier-profile',
            str(FIXTURE / 'carrier_profile_ref.json'),
            '--subject',
            str(SUBJECT_PATH),
        ],
        cwd=str(ROOT),
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith('carrier_profile_ref_ok:local_file_bundle:')
