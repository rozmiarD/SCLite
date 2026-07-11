from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import sclite._cli_impl as cli_module
from sclite import __version__
from sclite.artifacts import JsonSchemaValidationError, validate_artifact
from sclite.bundles import ReviewBundleError
from sclite.errors import SCLiteSchemaValidationError, SCLiteValidationError
from sclite.integrity import ChainVerificationError
from sclite.kernel_guard import KernelGuardError
from sclite.profiles import ProfileReferenceError
from sclite.review import ReviewRecordError
from sclite.secure import SecureBundleError, verify_secure_bundle_result
from sclite.testing import build_guarded_strict_verification_result_fixture
from sclite.tickets import TicketSemanticError, TicketUseVerificationError
from sclite.verification_result import VerificationResult, serialize_verification_result

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'examples' / 'govengine-integration'


def test_schema_validation_error_is_not_assertion_and_has_stable_code() -> None:
    with pytest.raises(JsonSchemaValidationError) as raised:
        validate_artifact({}, 'verification_result.v1.1')

    assert isinstance(raised.value, SCLiteSchemaValidationError)
    assert isinstance(raised.value, SCLiteValidationError)
    assert not isinstance(raised.value, AssertionError)
    assert raised.value.code == 'schema_validation_failed'


@pytest.mark.parametrize(
    ('error_type', 'code'),
    [
        (ReviewBundleError, 'review_bundle_failed'),
        (ReviewRecordError, 'review_record_failed'),
        (ChainVerificationError, 'chain_verification_failed'),
        (KernelGuardError, 'kernel_guard_failed'),
        (ProfileReferenceError, 'profile_reference_failed'),
        (SecureBundleError, 'secure_bundle_failed'),
        (TicketSemanticError, 'ticket_semantics_failed'),
        (TicketUseVerificationError, 'ticket_use_verification_failed'),
    ],
)
def test_public_validation_exception_code_matrix(
    error_type: type[SCLiteValidationError],
    code: str,
) -> None:
    error = error_type('invalid input')
    assert isinstance(error, ValueError)
    assert not isinstance(error, AssertionError)
    assert error.code == code


def test_schema_validation_cli_reports_stable_error_code(tmp_path: Path) -> None:
    artifact = tmp_path / 'invalid.json'
    artifact.write_text('{}\n', encoding='utf-8')
    result = subprocess.run(
        [
            sys.executable,
            '-m',
            'sclite.kernel_cli',
            'validate-artifact',
            '--schema',
            'verification_result.v1.1',
            str(artifact),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert 'error_code=schema_validation_failed' in result.stderr


def test_programmer_assertion_is_not_reclassified_as_validation_error() -> None:
    error = AssertionError('programmer bug')
    assert not isinstance(error, SCLiteValidationError)


def test_cli_does_not_swallow_programmer_assertion(monkeypatch: pytest.MonkeyPatch) -> None:
    def programmer_bug(*_args: object, **_kwargs: object) -> None:
        raise AssertionError('programmer bug')

    monkeypatch.setattr(cli_module, 'validate_artifact', programmer_bug)
    with pytest.raises(AssertionError, match='programmer bug'):
        cli_module.main([
            'validate-artifact',
            '--schema',
            'verification_result.v1.1',
            str(ROOT / 'sclite' / 'examples' / 'redaction-policy' / 'redaction_policy.json'),
        ])


def test_fixture_builder_is_explicitly_forgeable_and_not_a_typed_result() -> None:
    forged = build_guarded_strict_verification_result_fixture(
        {},
        secure_profile='forged-profile',
        security_posture='guarded_domain_auth',
    )

    assert forged['status'] == 'pass'
    assert forged['kernel_guard'] == 'pass'
    assert not isinstance(forged, VerificationResult)
    # Schema shape alone is not proof; a host must re-verify source material or
    # authenticate the result through a separately trusted channel.


def test_verification_result_type_is_not_an_unforgeable_token() -> None:
    forged = VerificationResult(
        profile='forged',
        security_posture='guarded_domain_auth',
        status='pass',
        artifact_chain='pass',
        strict_lifecycle='pass',
        kernel_guard='pass',
        ticket_use='pass',
        ticket_use_applicability='verified',
        replay='not_checked',
        entry_count=0,
        checked_entries=(),
        bundle_digest='0' * 64,
        guard_profile='forged',
        guard_root_tag='0' * 64,
        key_id='forged',
        policy='forged',
        verifier_version='forged',
        checks=('claimed_only',),
    )

    assert forged.status == 'pass'
    assert serialize_verification_result(forged)['status'] == 'pass'
    with pytest.raises(FrozenInstanceError):
        forged.status = 'fail'  # type: ignore[misc]


def test_production_typed_result_requires_real_verification(tmp_path: Path) -> None:
    # A copied public fixture has no Guard sidecar, so raw JSON or a forged type
    # cannot make the production verifier return a result.
    with pytest.raises(ValueError, match='missing kernel guard sidecar'):
        verify_secure_bundle_result(FIXTURE, key='x' * 32)


def test_serializer_emits_v1_1_provenance_contract() -> None:
    result = VerificationResult(
        profile='guarded-strict',
        security_posture='guarded_domain_auth',
        status='pass',
        artifact_chain='pass',
        strict_lifecycle='pass',
        kernel_guard='pass',
        ticket_use='review',
        ticket_use_applicability='not_applicable',
        replay='not_checked',
        entry_count=1,
        checked_entries=('intent_contract',),
        bundle_digest='a' * 64,
        guard_profile='kernel_guard_hmac_v1',
        guard_root_tag='b' * 64,
        key_id='key-1',
        policy='guarded-strict',
        verifier_version=__version__,
        checks=('artifact_chain',),
    )
    payload = serialize_verification_result(result)

    validate_artifact(payload, 'verification_result.v1.1', root=ROOT)
    validate_artifact(payload, 'verification_result.v1.1', root=ROOT, strict_jsonschema=True)
    assert payload['bundle_digest'] == 'a' * 64
    assert payload['policy'] == 'guarded-strict'
    assert payload['verifier_version'] == __version__
    assert payload['checks'] == ['artifact_chain']
    assert json.loads(json.dumps(payload)) == payload
