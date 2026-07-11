from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from ._json import VerificationLimits
from .artifacts import validate_artifact
from .bundles import review_bundle
from .integrity import artifact_descriptor, verify_artifact_chain_manifest, verify_lifecycle_manifest
from .secure import _verify_secure_bundle
from .schema_resolver import SchemaResolver
from .verification_result import VerificationResult


class VerificationPolicy(str, Enum):
    """Explicit verification posture selector; it is configuration, not authority."""

    INTEGRITY = "integrity"
    STRICT_LIFECYCLE = "strict_lifecycle"
    GUARDED_LIFECYCLE = "guarded_lifecycle"
    PUBLIC_REVIEW = "public_review"


@dataclass(frozen=True, slots=True)
class ArtifactDescriptor:
    artifact_type: str
    schema_version: str
    schema_ref: str
    canonicalization: str
    algorithm: str
    digest: str
    canonical_bytes: int

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> ArtifactDescriptor:
        return cls(
            artifact_type=str(value.get("artifact_type") or ""),
            schema_version=str(value.get("schema_version") or ""),
            schema_ref=str(value.get("schema_ref") or ""),
            canonicalization=str(value.get("canonicalization") or ""),
            algorithm=str(value.get("algorithm") or ""),
            digest=str(value.get("digest") or ""),
            canonical_bytes=int(value.get("canonical_bytes") or 0),
        )


@dataclass(frozen=True, slots=True)
class VerifiedArtifact:
    descriptor: ArtifactDescriptor
    schema_ref: str
    strict_jsonschema: bool
    checks: tuple[str, ...]
    status: str = "pass"
    authentication: str = "not_claimed"
    runtime_authority: str = "not_claimed"


@dataclass(frozen=True, slots=True)
class VerifiedBundle:
    policy: VerificationPolicy
    status: str
    result: Mapping[str, Any]
    verification_result: VerificationResult | None = None
    authentication: str = "not_claimed"
    runtime_authority: str = "not_claimed"


def verify_artifact(
    value: Mapping[str, Any],
    *,
    schema_ref: str,
    root: Path | None = None,
    strict_jsonschema: bool = False,
    resolver: SchemaResolver | None = None,
) -> VerifiedArtifact:
    validate_artifact(
        dict(value), schema_ref, root=root, strict_jsonschema=strict_jsonschema, resolver=resolver
    )
    descriptor = ArtifactDescriptor.from_mapping(artifact_descriptor(value))
    return VerifiedArtifact(
        descriptor=descriptor,
        schema_ref=schema_ref,
        strict_jsonschema=strict_jsonschema,
        checks=("artifact_schema", "canonical_descriptor"),
    )


def verify_bundle(
    target: Mapping[str, Any] | Path | str,
    *,
    policy: VerificationPolicy,
    root: Path | None = None,
    key: str | bytes | None = None,
    guard_path: Path | str | None = None,
    strict_jsonschema: bool = False,
    verification_limits: VerificationLimits | None = None,
) -> VerifiedBundle:
    if not isinstance(policy, VerificationPolicy):
        raise ValueError(f"unsupported verification policy: {policy!r}")
    if policy in {VerificationPolicy.INTEGRITY, VerificationPolicy.STRICT_LIFECYCLE}:
        if not isinstance(target, Mapping):
            raise TypeError(f"{policy.value} requires a manifest mapping")
        if policy is VerificationPolicy.INTEGRITY:
            result = verify_artifact_chain_manifest(
                target,
                root=root,
                strict_jsonschema=strict_jsonschema,
                verification_limits=verification_limits,
            )
        else:
            result = verify_lifecycle_manifest(
                target,
                root=root,
                strict_jsonschema=strict_jsonschema,
                verification_limits=verification_limits,
            )
        return _verified_bundle(policy, result)
    if policy is VerificationPolicy.GUARDED_LIFECYCLE:
        if isinstance(target, Mapping):
            raise TypeError("guarded_lifecycle requires a filesystem target")
        if key is None:
            raise TypeError("guarded_lifecycle requires an explicit key")
        response, typed_result = _verify_secure_bundle(
            target,
            guard_path=guard_path,
            key=key,
            root=root,
            strict_jsonschema=strict_jsonschema,
            verification_limits=verification_limits,
        )
        return _verified_bundle(policy, response, verification_result=typed_result)
    if policy is VerificationPolicy.PUBLIC_REVIEW:
        if isinstance(target, Mapping):
            raise TypeError("public_review requires a bundle directory")
        result = review_bundle(
            target,
            strict_jsonschema=strict_jsonschema,
            mode="public_export",
            verification_limits=verification_limits,
        )
        return _verified_bundle(policy, result)
    raise ValueError(f"unsupported verification policy: {policy!r}")


def _verified_bundle(
    policy: VerificationPolicy,
    result: Mapping[str, Any],
    *,
    verification_result: VerificationResult | None = None,
) -> VerifiedBundle:
    status = str(result.get("status") or result.get("verdict") or "pass")
    return VerifiedBundle(
        policy=policy,
        status=status,
        result=MappingProxyType(dict(result)),
        verification_result=verification_result,
    )
