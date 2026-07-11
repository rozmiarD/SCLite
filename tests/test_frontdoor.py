from __future__ import annotations

import json
from pathlib import Path

import pytest

from sclite import (
    ArtifactDescriptor,
    VerificationPolicy,
    VerifiedArtifact,
    VerifiedBundle,
    verify_artifact,
    verify_bundle,
)
from sclite.integrity import verify_artifact_chain_manifest, verify_lifecycle_manifest


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "sclite" / "examples" / "contract-lifecycle-v0.2"


def _manifest() -> dict:
    return json.loads((BUNDLE / "artifact_chain_manifest.json").read_text(encoding="utf-8"))


def test_verify_artifact_returns_typed_non_authority_result() -> None:
    value = json.loads((BUNDLE / "intent_contract.json").read_text(encoding="utf-8"))

    result = verify_artifact(value, schema_ref="schemas/intent_contract.v0.2.schema.json")

    assert isinstance(result, VerifiedArtifact)
    assert isinstance(result.descriptor, ArtifactDescriptor)
    assert result.status == "pass"
    assert result.authentication == "not_claimed"
    assert result.runtime_authority == "not_claimed"


@pytest.mark.parametrize(
    ("policy", "legacy"),
    [
        (VerificationPolicy.INTEGRITY, verify_artifact_chain_manifest),
        (VerificationPolicy.STRICT_LIFECYCLE, verify_lifecycle_manifest),
    ],
)
def test_verify_bundle_is_equivalent_to_legacy_wrapper(policy, legacy) -> None:
    manifest = _manifest()

    typed = verify_bundle(manifest, policy=policy, root=BUNDLE)

    assert isinstance(typed, VerifiedBundle)
    assert dict(typed.result) == legacy(manifest, root=BUNDLE)
    assert typed.policy is policy
    assert typed.authentication == "not_claimed"
    assert typed.runtime_authority == "not_claimed"


def test_explicit_policy_cannot_be_implicitly_downgraded() -> None:
    with pytest.raises(ValueError, match="unsupported verification policy"):
        verify_bundle(_manifest(), policy="integrity")  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="requires a manifest mapping"):
        verify_bundle(BUNDLE, policy=VerificationPolicy.STRICT_LIFECYCLE)

    with pytest.raises(TypeError, match="explicit key"):
        verify_bundle(BUNDLE, policy=VerificationPolicy.GUARDED_LIFECYCLE)
