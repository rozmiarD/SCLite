from __future__ import annotations

import json
from pathlib import Path

import pytest

from sclite.profiles import ProfileReferenceError, validate_carrier_profile_ref, validate_trust_profile_ref

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'examples' / 'govengine-integration'
SUBJECT = FIXTURE / '04_execution_ticket.json'


def _load(name: str) -> dict:
    value = json.loads((FIXTURE / name).read_text(encoding='utf-8'))
    assert isinstance(value, dict)
    return value


def _subject() -> dict:
    value = json.loads(SUBJECT.read_text(encoding='utf-8'))
    assert isinstance(value, dict)
    return value


def test_trust_profile_ref_rejects_subject_descriptor_drift() -> None:
    ref = _load('trust_profile_ref.json')
    ref['links']['subject']['descriptor']['digest'] = '0' * 64
    with pytest.raises(ProfileReferenceError, match='subject descriptor mismatch'):
        validate_trust_profile_ref(ref, _subject())


def test_carrier_profile_ref_rejects_subject_digest_drift() -> None:
    ref = _load('carrier_profile_ref.json')
    ref['integrity']['subject_artifact_digest'] = '0' * 64
    with pytest.raises(ProfileReferenceError, match='subject_artifact_digest mismatch'):
        validate_carrier_profile_ref(ref, _subject())


def test_carrier_profile_ref_rejects_unsupported_profile() -> None:
    ref = _load('carrier_profile_ref.json')
    ref['carrier_profile'] = 'telegram_bot_magic_transport'
    with pytest.raises(Exception):
        validate_carrier_profile_ref(ref, _subject())


def test_trust_profile_ref_rejects_missing_subject_descriptor() -> None:
    ref = _load('trust_profile_ref.json')
    del ref['links']['subject']['descriptor']
    with pytest.raises(Exception):
        validate_trust_profile_ref(ref, _subject())


def test_carrier_profile_ref_rejects_missing_links_subject() -> None:
    ref = _load('carrier_profile_ref.json')
    del ref['links']['subject']
    with pytest.raises(Exception):
        validate_carrier_profile_ref(ref, _subject())
