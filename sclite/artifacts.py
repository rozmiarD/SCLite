from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping

ARTIFACT_CANONICALIZATION_VERSION = 'sclite-json-v0.1'
ARTIFACT_HASH_ALGORITHM = 'sha256'

SCHEMA_FILES = {
    'scope_fidelity_report.v0.1': 'scope_fidelity_report.v0.1.schema.json',
    'scope_fidelity_report.v0.2': 'scope_fidelity_report.v0.2.schema.json',
    'review_record.v0.1': 'review_record.v0.1.schema.json',
    'redaction_policy.v0.1': 'redaction_policy.v0.1.schema.json',
    'redaction_receipt.v0.1': 'redaction_receipt.v0.1.schema.json',
    'public_validation_surface_index.v0.1': 'public_validation_surface_index.v0.1.schema.json',
    'public_snapshot_manifest.v0.1': 'public_snapshot_manifest.v0.1.schema.json',
    'intent_contract.v0.2': 'intent_contract.v0.2.schema.json',
    'policy_decision.v0.2': 'policy_decision.v0.2.schema.json',
    'execution_contract.v0.2': 'execution_contract.v0.2.schema.json',
    'execution_ticket.v0.2': 'execution_ticket.v0.2.schema.json',
    'execution_ticket.v0.3': 'execution_ticket.v0.3.schema.json',
    'execution_receipt.v0.2': 'execution_receipt.v0.2.schema.json',
    'evidence_contract.v0.2': 'evidence_contract.v0.2.schema.json',
    'artifact_chain_manifest.v0.2': 'artifact_chain_manifest.v0.2.schema.json',
    'verification_result.v1': 'verification_result.v1.schema.json',
    'trust_profile_ref.v0.1': 'trust_profile_ref.v0.1.schema.json',
    'carrier_profile_ref.v0.1': 'carrier_profile_ref.v0.1.schema.json',
}


class JsonSchemaValidationError(AssertionError):
    pass


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


def validate_json_schema_value(schema: Mapping[str, Any], value: Any, path: str = '$') -> None:
    """Validate the JSON Schema subset used by SCL v0.1 artifacts."""
    if 'const' in schema and value != schema['const']:
        raise JsonSchemaValidationError(f'{path}: expected const {schema["const"]!r}, got {value!r}')
    if 'enum' in schema and value not in schema['enum']:
        raise JsonSchemaValidationError(f'{path}: expected one of {schema["enum"]!r}, got {value!r}')
    if 'type' in schema:
        _assert_json_schema_type(value, schema['type'], path)
    if isinstance(value, str) and 'minLength' in schema and len(value) < int(schema['minLength']):
        raise JsonSchemaValidationError(f'{path}: expected minLength {schema["minLength"]}')
    if isinstance(value, (int, float)) and not isinstance(value, bool) and 'minimum' in schema and value < float(schema['minimum']):
        raise JsonSchemaValidationError(f'{path}: expected minimum {schema["minimum"]}')
    if schema.get('type') == 'object':
        if not isinstance(value, dict):
            raise JsonSchemaValidationError(f'{path}: expected object')
        for key in schema.get('required', []):
            if key not in value:
                raise JsonSchemaValidationError(f'{path}: missing required field {key!r}')
        properties = schema.get('properties') if isinstance(schema.get('properties'), dict) else {}
        for key, subschema in properties.items():
            if key in value and isinstance(subschema, dict):
                validate_json_schema_value(subschema, value[key], f'{path}.{key}')
        if schema.get('additionalProperties') is False:
            extra = sorted(set(value) - set(properties))
            if extra:
                raise JsonSchemaValidationError(f'{path}: unexpected fields {extra!r}')
    if schema.get('type') == 'array':
        if not isinstance(value, list):
            raise JsonSchemaValidationError(f'{path}: expected array')
        item_schema = schema.get('items')
        if isinstance(item_schema, dict):
            for idx, item in enumerate(value):
                validate_json_schema_value(item_schema, item, f'{path}[{idx}]')


def _resolve_schema_ref(schema_ref: str, *, root: Path | None = None) -> Path:
    raw_ref = str(schema_ref or '')
    candidates: List[Path] = []
    if root is not None:
        candidates.append(root / raw_ref)
    candidates.append(repo_root() / raw_ref)
    basename = Path(raw_ref).name
    if raw_ref in SCHEMA_FILES:
        basename = SCHEMA_FILES[raw_ref]
    candidates.append(schema_dir() / basename)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def load_json_schema(schema_ref: str, *, root: Path | None = None) -> Dict[str, Any]:
    schema_path = _resolve_schema_ref(schema_ref, root=root)
    value = json.loads(schema_path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise JsonSchemaValidationError(f'{schema_ref}: schema root is not an object')
    return value


def validate_schema_ref(
    schema_ref: str,
    value: Any,
    *,
    root: Path | None = None,
    path: str = '$',
    strict_jsonschema: bool = False,
) -> None:
    schema = load_json_schema(schema_ref, root=root)
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
    validate_json_schema_value(schema, value, path=path)


def validate_artifact(value: Any, schema_name: str, *, root: Path | None = None, strict_jsonschema: bool = False) -> None:
    """Validate one artifact against a named SCL schema.

    By default this uses SCLite's dependency-free schema subset validator.
    Pass strict_jsonschema=True to use Draft 2020-12 validation via the
    optional jsonschema extra.
    """
    validate_schema_ref(schema_name, value, root=root, strict_jsonschema=strict_jsonschema)


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
