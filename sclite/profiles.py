from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping

from .artifacts import JsonSchemaValidationError, validate_artifact
from .errors import SCLiteValidationError
from .integrity import artifact_descriptor
from .json_types import json_array, json_mapping

TRUST_PROFILE_REF_SCHEMA = 'trust_profile_ref.v0.1'
CARRIER_PROFILE_REF_SCHEMA = 'carrier_profile_ref.v0.1'
TRUST_PROFILE_REF_SCHEMA_V0_2 = 'trust_profile_ref.v0.2'
CARRIER_PROFILE_REF_SCHEMA_V0_2 = 'carrier_profile_ref.v0.2'
TRUST_PROFILES = {
    'none',
    'digest_only',
    'local_ed25519_ref',
    'dsse_envelope_ref',
    'sigstore_bundle_ref',
    'external_verifier',
}
CARRIER_PROFILES = {
    'local_file_bundle',
    'ci_artifact_bundle',
    'github_artifact',
    'govengine_bundle',
    'ravenclaw_review_bundle',
    'tecrax_review_bundle',
    'openclaw_carrier_payload',
    'mcp_message_ref',
    'a2a_message_ref',
}

OPAQUE_PROFILE_IDENTIFIER_PATTERN = re.compile(
    r'^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*/[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*@v[0-9]+(?:\.[0-9]+)*$'
)


class ProfileReferenceError(SCLiteValidationError):
    """Raised when a trust/carrier profile reference is not digest-bound."""

    default_code = 'profile_reference_failed'


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProfileReferenceError(f'{label} must be an object')
    return value


def _subject_descriptor(profile_ref: Mapping[str, Any]) -> Mapping[str, Any]:
    links = _require_mapping(profile_ref.get('links'), 'profile_ref.links')
    subject = _require_mapping(links.get('subject'), 'profile_ref.links.subject')
    return _require_mapping(subject.get('descriptor'), 'profile_ref.links.subject.descriptor')


def _validate_subject_binding(profile_ref: Mapping[str, Any], subject_artifact: Mapping[str, Any]) -> None:
    expected = artifact_descriptor(subject_artifact)
    actual = dict(_subject_descriptor(profile_ref))
    if actual != expected:
        raise ProfileReferenceError('profile reference subject descriptor mismatch')
    integrity = _require_mapping(profile_ref.get('integrity'), 'profile_ref.integrity')
    digest = str(integrity.get('subject_artifact_digest') or '')
    if digest != expected['digest']:
        raise ProfileReferenceError('profile reference subject_artifact_digest mismatch')


def validate_trust_profile_ref(
    profile_ref: Mapping[str, Any],
    subject_artifact: Mapping[str, Any],
    *,
    strict_jsonschema: bool = False,
) -> List[str]:
    """Validate a sidecar trust-profile reference against a subject artifact.

    This only validates profile shape and digest binding. SCLite does not
    decide signer identity, PKI trust, revocation, or whether a verifier should
    accept the referenced signature/bundle.
    """
    try:
        schema_version = str(profile_ref.get('schema_version') or '')
        schema = TRUST_PROFILE_REF_SCHEMA_V0_2 if schema_version == 'v0.2' else TRUST_PROFILE_REF_SCHEMA
        validate_artifact(dict(profile_ref), schema, strict_jsonschema=strict_jsonschema)
    except JsonSchemaValidationError:
        raise
    profile = str(profile_ref.get('trust_profile') or '')
    if schema_version == 'v0.2' and OPAQUE_PROFILE_IDENTIFIER_PATTERN.fullmatch(profile) is None:
        raise ProfileReferenceError(f'invalid opaque trust_profile identifier: {profile}')
    if schema_version != 'v0.2' and profile not in TRUST_PROFILES:
        raise ProfileReferenceError(f'unsupported trust_profile: {profile}')
    _validate_subject_binding(profile_ref, subject_artifact)
    return [
        'trust_profile_schema_valid',
        'trust_profile_identifier_valid',
        'trust_profile_supported',
        'trust_profile_subject_descriptor_bound',
        'trust_profile_subject_digest_bound',
    ]


def validate_carrier_profile_ref(
    profile_ref: Mapping[str, Any],
    subject_artifact: Mapping[str, Any],
    *,
    strict_jsonschema: bool = False,
) -> List[str]:
    """Validate a sidecar carrier-profile reference against a subject artifact.

    This only validates profile shape and digest binding. SCLite does not
    transport artifacts, verify a remote carrier, implement a protocol adapter,
    or prove delivery.
    """
    try:
        schema_version = str(profile_ref.get('schema_version') or '')
        schema = CARRIER_PROFILE_REF_SCHEMA_V0_2 if schema_version == 'v0.2' else CARRIER_PROFILE_REF_SCHEMA
        validate_artifact(dict(profile_ref), schema, strict_jsonschema=strict_jsonschema)
    except JsonSchemaValidationError:
        raise
    profile = str(profile_ref.get('carrier_profile') or '')
    if schema_version == 'v0.2' and OPAQUE_PROFILE_IDENTIFIER_PATTERN.fullmatch(profile) is None:
        raise ProfileReferenceError(f'invalid opaque carrier_profile identifier: {profile}')
    if schema_version != 'v0.2' and profile not in CARRIER_PROFILES:
        raise ProfileReferenceError(f'unsupported carrier_profile: {profile}')
    _validate_subject_binding(profile_ref, subject_artifact)
    return [
        'carrier_profile_schema_valid',
        'carrier_profile_identifier_valid',
        'carrier_profile_supported',
        'carrier_profile_subject_descriptor_bound',
        'carrier_profile_subject_digest_bound',
    ]


def profile_ref_summary(profile_ref: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a compact JSON-safe trust/carrier profile summary."""
    integrity = json_mapping(profile_ref.get('integrity'))
    return {
        'artifact_type': profile_ref.get('artifact_type'),
        'schema_version': profile_ref.get('schema_version'),
        'profile': profile_ref.get('trust_profile') or profile_ref.get('carrier_profile'),
        'subject_artifact_digest': integrity.get('subject_artifact_digest'),
        'non_claims': json_array(profile_ref.get('non_claims')),
    }


def translate_legacy_profile_ref(profile_ref: Mapping[str, Any]) -> Dict[str, Any]:
    """Translate a v0.1 closed identifier to the neutral v0.2 bridge shape."""
    translated = dict(profile_ref)
    artifact_type = str(translated.get('artifact_type') or '')
    if artifact_type == 'trust_profile_ref':
        field = 'trust_profile'
        schema_ref = 'schemas/trust_profile_ref.v0.2.schema.json'
    elif artifact_type == 'carrier_profile_ref':
        field = 'carrier_profile'
        schema_ref = 'schemas/carrier_profile_ref.v0.2.schema.json'
    else:
        raise ProfileReferenceError(f'unsupported profile reference artifact_type: {artifact_type}')
    legacy = str(translated.get(field) or '')
    translated['schema_version'] = 'v0.2'
    translated['schema_ref'] = schema_ref
    translated[field] = f'legacy.sclite/{legacy}@v1'
    return translated


def normalized_profile_binding(profile_ref: Mapping[str, Any]) -> tuple[str, str]:
    """Return an exact opaque binding; parsing and classification remain host-owned."""
    artifact_type = str(profile_ref.get('artifact_type') or '')
    field = 'trust_profile' if artifact_type == 'trust_profile_ref' else 'carrier_profile'
    return artifact_type, str(profile_ref.get(field) or '')
