from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Mapping

from ._json import load_json_object
from .errors import SCLiteSchemaValidationError
from .json_types import json_mapping

ARTIFACT_CANONICALIZATION_VERSION = 'sclite-json-v0.1'
ARTIFACT_HASH_ALGORITHM = 'sha256'

SCHEMA_FILES = {
    'scope_fidelity_report.v0.1': 'scope_fidelity_report.v0.1.schema.json',
    'scope_fidelity_report.v0.2': 'scope_fidelity_report.v0.2.schema.json',
    'review_record.v0.1': 'review_record.v0.1.schema.json',
    'redaction_policy.v0.1': 'redaction_policy.v0.1.schema.json',
    'redaction_policy.v0.2': 'redaction_policy.v0.2.schema.json',
    'redaction_receipt.v0.1': 'redaction_receipt.v0.1.schema.json',
    'redaction_receipt.v0.2': 'redaction_receipt.v0.2.schema.json',
    'public_validation_surface_index.v0.1': 'public_validation_surface_index.v0.1.schema.json',
    'public_validation_surface_index.v0.2': 'public_validation_surface_index.v0.2.schema.json',
    'public_snapshot_manifest.v0.1': 'public_snapshot_manifest.v0.1.schema.json',
    'public_snapshot_manifest.v0.2': 'public_snapshot_manifest.v0.2.schema.json',
    'intent_contract.v0.2': 'intent_contract.v0.2.schema.json',
    'policy_decision.v0.2': 'policy_decision.v0.2.schema.json',
    'execution_contract.v0.2': 'execution_contract.v0.2.schema.json',
    'execution_ticket.v0.2': 'execution_ticket.v0.2.schema.json',
    'execution_ticket.v0.3': 'execution_ticket.v0.3.schema.json',
    'execution_receipt.v0.2': 'execution_receipt.v0.2.schema.json',
    'evidence_contract.v0.2': 'evidence_contract.v0.2.schema.json',
    'artifact_chain_manifest.v0.2': 'artifact_chain_manifest.v0.2.schema.json',
    'verification_result.v1': 'verification_result.v1.schema.json',
    'verification_result.v1.1': 'verification_result.v1.1.schema.json',
    'kernel_guard_hmac_v1': 'kernel_guard_hmac_v1.schema.json',
    'trust_profile_ref.v0.1': 'trust_profile_ref.v0.1.schema.json',
    'carrier_profile_ref.v0.1': 'carrier_profile_ref.v0.1.schema.json',
    'observation_envelope.v0.1': 'observation_envelope.v0.1.schema.json',
    'finding.v0.1': 'finding.v0.1.schema.json',
    'reaction_plan.v0.1': 'reaction_plan.v0.1.schema.json',
    'escalation_proposal.v0.1': 'escalation_proposal.v0.1.schema.json',
    'trigger_decision.v0.1': 'trigger_decision.v0.1.schema.json',
    'watchdog_decision.v0.1': 'watchdog_decision.v0.1.schema.json',
    'automation_chain.v0.1': 'automation_chain.v0.1.schema.json',
}


class JsonSchemaValidationError(SCLiteSchemaValidationError):
    """Compatibility name for schema validation failures through SCLite 2.0."""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def package_root() -> Path:
    return Path(__file__).resolve().parent


def schema_dir() -> Path:
    return package_root() / 'schemas'


def examples_dir() -> Path:
    return package_root() / 'examples'


def _json_type_name(value: Any) -> str:
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, dict):
        return 'object'
    if isinstance(value, list):
        return 'array'
    if isinstance(value, int) and not isinstance(value, bool):
        return 'integer'
    if isinstance(value, float):
        return 'number'
    if isinstance(value, str):
        return 'string'
    if value is None:
        return 'null'
    return type(value).__name__


def _assert_json_schema_type(value: Any, expected: Any, path: str) -> None:
    expected_types = expected if isinstance(expected, list) else [expected]
    actual = _json_type_name(value)
    if actual == 'integer' and 'number' in expected_types:
        return
    if actual not in expected_types:
        raise JsonSchemaValidationError(f'{path}: expected {expected_types}, got {actual}')


def _resolve_local_ref(root_schema: Mapping[str, Any], ref: str) -> Mapping[str, Any]:
    if not ref.startswith('#/'):
        raise JsonSchemaValidationError(f'{ref}: only local JSON Schema refs are supported by the dependency-free validator')
    current: Any = root_schema
    for raw_part in ref[2:].split('/'):
        part = raw_part.replace('~1', '/').replace('~0', '~')
        if not isinstance(current, Mapping) or part not in current:
            raise JsonSchemaValidationError(f'{ref}: unresolved JSON Schema ref')
        current = current[part]
    if not isinstance(current, Mapping):
        raise JsonSchemaValidationError(f'{ref}: JSON Schema ref does not resolve to an object')
    return current


def validate_json_schema_value(
    schema: Mapping[str, Any],
    value: Any,
    path: str = '$',
    *,
    root_schema: Mapping[str, Any] | None = None,
) -> None:
    """Validate the JSON Schema subset used by SCL v0.1 artifacts."""
    root = root_schema or schema
    if '$ref' in schema:
        validate_json_schema_value(_resolve_local_ref(root, str(schema['$ref'])), value, path, root_schema=root)
        return
    if 'const' in schema and value != schema['const']:
        raise JsonSchemaValidationError(f'{path}: expected const {schema["const"]!r}, got {value!r}')
    if 'enum' in schema and value not in schema['enum']:
        raise JsonSchemaValidationError(f'{path}: expected one of {schema["enum"]!r}, got {value!r}')
    if 'type' in schema:
        _assert_json_schema_type(value, schema['type'], path)
    if isinstance(value, str) and 'minLength' in schema and len(value) < int(schema['minLength']):
        raise JsonSchemaValidationError(f'{path}: expected minLength {schema["minLength"]}')
    if isinstance(value, str) and 'maxLength' in schema and len(value) > int(schema['maxLength']):
        raise JsonSchemaValidationError(f'{path}: expected maxLength {schema["maxLength"]}')
    if isinstance(value, str) and 'pattern' in schema:
        pattern = str(schema['pattern'])
        if re.search(pattern, value) is None:
            raise JsonSchemaValidationError(f'{path}: expected pattern {pattern!r}')
    if isinstance(value, (int, float)) and not isinstance(value, bool) and 'minimum' in schema and value < float(schema['minimum']):
        raise JsonSchemaValidationError(f'{path}: expected minimum {schema["minimum"]}')
    if isinstance(value, (int, float)) and not isinstance(value, bool) and 'maximum' in schema and value > float(schema['maximum']):
        raise JsonSchemaValidationError(f'{path}: expected maximum {schema["maximum"]}')
    if schema.get('type') == 'object':
        if not isinstance(value, dict):
            raise JsonSchemaValidationError(f'{path}: expected object')
        for key in schema.get('required', []):
            if key not in value:
                raise JsonSchemaValidationError(f'{path}: missing required field {key!r}')
        properties = json_mapping(schema.get('properties'))
        for key, subschema in properties.items():
            if key in value and isinstance(subschema, dict):
                validate_json_schema_value(subschema, value[key], f'{path}.{key}', root_schema=root)
        if schema.get('additionalProperties') is False:
            extra = sorted(set(value) - set(properties))
            if extra:
                raise JsonSchemaValidationError(f'{path}: unexpected fields {extra!r}')
    if schema.get('type') == 'array':
        if not isinstance(value, list):
            raise JsonSchemaValidationError(f'{path}: expected array')
        if 'minItems' in schema and len(value) < int(schema['minItems']):
            raise JsonSchemaValidationError(f'{path}: expected minItems {schema["minItems"]}')
        if 'maxItems' in schema and len(value) > int(schema['maxItems']):
            raise JsonSchemaValidationError(f'{path}: expected maxItems {schema["maxItems"]}')
        item_schema = schema.get('items')
        if isinstance(item_schema, dict):
            for idx, item in enumerate(value):
                validate_json_schema_value(item_schema, item, f'{path}[{idx}]', root_schema=root)


def _packaged_schema_path(schema_ref: str) -> Path | None:
    raw_ref = str(schema_ref or '')
    if raw_ref in SCHEMA_FILES:
        return schema_dir() / SCHEMA_FILES[raw_ref]
    for filename in set(SCHEMA_FILES.values()):
        if raw_ref in {filename, f'schemas/{filename}'}:
            return schema_dir() / filename
    return None


def _resolve_schema_ref(
    schema_ref: str,
    *,
    root: Path | None = None,
    allow_external_schema_refs: bool = False,
) -> Path:
    raw_ref = str(schema_ref or '')
    packaged = _packaged_schema_path(raw_ref)
    if packaged is not None:
        return packaged
    if not allow_external_schema_refs:
        raise JsonSchemaValidationError(
            f'{schema_ref}: not a packaged SCLite schema; '
            'external schema refs require allow_external_schema_refs=True'
        )

    raw_path = Path(raw_ref)
    if root is not None:
        base = Path(root).resolve()
        candidate = raw_path.resolve() if raw_path.is_absolute() else (base / raw_path).resolve()
        try:
            candidate.relative_to(base)
        except ValueError as exc:
            raise JsonSchemaValidationError(f'{schema_ref}: external schema path escapes root') from exc
    else:
        candidate = raw_path.resolve()
    if candidate.exists():
        return candidate
    raise JsonSchemaValidationError(f'{schema_ref}: schema file not found')


def load_json_schema(
    schema_ref: str,
    *,
    root: Path | None = None,
    allow_external_schema_refs: bool = False,
) -> Dict[str, Any]:
    schema_path = _resolve_schema_ref(
        schema_ref,
        root=root,
        allow_external_schema_refs=allow_external_schema_refs,
    )
    return load_json_object(schema_path, error_cls=JsonSchemaValidationError)


def validate_schema_ref(
    schema_ref: str,
    value: Any,
    *,
    root: Path | None = None,
    path: str = '$',
    strict_jsonschema: bool = False,
    allow_external_schema_refs: bool = False,
) -> None:
    schema = load_json_schema(
        schema_ref,
        root=root,
        allow_external_schema_refs=allow_external_schema_refs,
    )
    if strict_jsonschema:
        try:
            import jsonschema
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise JsonSchemaValidationError(
                "strict JSON Schema validation requires the optional 'jsonschema' dependency; "
                "install with: pip install 'sclite-core[jsonschema]'"
            ) from exc
        try:
            jsonschema.Draft202012Validator(schema).validate(value)
        except jsonschema.ValidationError as exc:
            location = '.'.join(str(part) for part in exc.absolute_path) or path
            raise JsonSchemaValidationError(f'{location}: {exc.message}') from exc
        return
    validate_json_schema_value(schema, value, path=path, root_schema=schema)


def validate_artifact(
    value: Any,
    schema_name: str,
    *,
    root: Path | None = None,
    strict_jsonschema: bool = False,
    allow_external_schema_refs: bool = False,
) -> None:
    """Validate one artifact against a named SCL schema.

    By default this uses SCLite's dependency-free schema subset validator.
    Pass strict_jsonschema=True to use Draft 2020-12 validation via the
    optional jsonschema extra. Bundle-provided schema references resolve to
    packaged SCLite schemas by default; set allow_external_schema_refs=True
    only for caller-controlled local schema paths.
    """
    validate_schema_ref(
        schema_name,
        value,
        root=root,
        strict_jsonschema=strict_jsonschema,
        allow_external_schema_refs=allow_external_schema_refs,
    )


def canonicalize_artifact(value: Any) -> str:
    """Return deterministic compact JSON for a JSON-compatible artifact.

    The v0.1 canonicalization is intentionally small: UTF-8 JSON with sorted
    object keys, compact separators, preserved Unicode, and no NaN/Infinity.
    It is a content-addressing helper, not a signature or tamper-proof proof.
    """
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def canonical_artifact_bytes(value: Any) -> bytes:
    """Return UTF-8 bytes for the v0.1 canonical JSON representation."""
    return canonicalize_artifact(value).encode('utf-8')


def artifact_sha256(value: Any) -> str:
    """Return SHA-256 hex digest over v0.1 canonical artifact bytes."""
    return hashlib.sha256(canonical_artifact_bytes(value)).hexdigest()


def build_artifact_hash(value: Any) -> Dict[str, Any]:
    """Return a public-safe hash descriptor for one JSON-compatible artifact."""
    canonical = canonical_artifact_bytes(value)
    return {
        'canonicalization': ARTIFACT_CANONICALIZATION_VERSION,
        'algorithm': ARTIFACT_HASH_ALGORITHM,
        'digest': hashlib.sha256(canonical).hexdigest(),
        'canonical_bytes': len(canonical),
    }
