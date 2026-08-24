from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, Mapping

from ._json import load_json_object
from .errors import SCLiteSchemaValidationError, SCLiteValidationError
from .json_types import json_mapping
from .schema_resolver import SchemaResolutionError, SchemaResolver

ARTIFACT_CANONICALIZATION_VERSION = 'sclite-json-v0.1'
ARTIFACT_CANONICALIZATION_V2 = 'sclite-json-v0.2'
ARTIFACT_HASH_ALGORITHM = 'sha256'
_MAX_SAFE_JSON_INTEGER = (1 << 53) - 1

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
    'policy_decision.v0.3': 'policy_decision.v0.3.schema.json',
    'execution_contract.v0.2': 'execution_contract.v0.2.schema.json',
    'execution_contract.v0.3': 'execution_contract.v0.3.schema.json',
    'execution_ticket.v0.2': 'execution_ticket.v0.2.schema.json',
    'execution_ticket.v0.3': 'execution_ticket.v0.3.schema.json',
    'execution_receipt.v0.2': 'execution_receipt.v0.2.schema.json',
    'evidence_contract.v0.2': 'evidence_contract.v0.2.schema.json',
    'artifact_chain_manifest.v0.2': 'artifact_chain_manifest.v0.2.schema.json',
    'verification_result.v1': 'verification_result.v1.schema.json',
    'verification_result.v1.1': 'verification_result.v1.1.schema.json',
    'kernel_guard_hmac_v1': 'kernel_guard_hmac_v1.schema.json',
    'trust_profile_ref.v0.1': 'trust_profile_ref.v0.1.schema.json',
    'trust_profile_ref.v0.2': 'trust_profile_ref.v0.2.schema.json',
    'carrier_profile_ref.v0.1': 'carrier_profile_ref.v0.1.schema.json',
    'carrier_profile_ref.v0.2': 'carrier_profile_ref.v0.2.schema.json',
}


class JsonSchemaValidationError(SCLiteSchemaValidationError):
    """Compatibility name for schema validation failures through SCLite 2.0."""


def require_json_integer(
    value: Any,
    *,
    label: str,
    error_cls: type[SCLiteValidationError] = SCLiteValidationError,
) -> int:
    """Return a JSON integer without Python or string coercion.

    JSON booleans are distinct from integers even though ``bool`` subclasses
    ``int`` in Python.  This boundary is deliberately shared by artifact
    verifiers so caller-controlled values never reach ``int(...)`` coercion.
    """
    if type(value) is not int:
        raise error_cls(
            f'{label} must be a JSON integer (boolean and string values are not accepted)',
            code='invalid_json_integer',
        )
    return value


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


def _json_values_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without Python's bool-as-int equivalence."""
    left_type = _json_type_name(left)
    right_type = _json_type_name(right)
    number_types = {'integer', 'number'}
    if left_type != right_type and {left_type, right_type} != number_types:
        return False
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return (
            set(left) == set(right)
            and all(_json_values_equal(left[key], right[key]) for key in left)
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            _json_values_equal(left_item, right_item)
            for left_item, right_item in zip(left, right)
        )
    return bool(left == right)


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
    if 'const' in schema and not _json_values_equal(value, schema['const']):
        raise JsonSchemaValidationError(f'{path}: expected const {schema["const"]!r}, got {value!r}')
    if 'enum' in schema and not any(_json_values_equal(value, item) for item in schema['enum']):
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
    resolver: SchemaResolver | None = None,
) -> Dict[str, Any]:
    if resolver is not None:
        try:
            return dict(resolver.resolve(schema_ref))
        except SchemaResolutionError as exc:
            raise JsonSchemaValidationError(str(exc)) from exc
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
    resolver: SchemaResolver | None = None,
) -> None:
    schema = load_json_schema(
        schema_ref,
        root=root,
        allow_external_schema_refs=allow_external_schema_refs,
        resolver=resolver,
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
    resolver: SchemaResolver | None = None,
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
        resolver=resolver,
    )


def canonicalize_artifact(value: Any) -> str:
    """Return deterministic compact JSON for a JSON-compatible artifact.

    The v0.1 canonicalization is intentionally small: UTF-8 JSON with sorted
    object keys, compact separators, preserved Unicode, and no NaN/Infinity.
    It is a content-addressing helper, not a signature or tamper-proof proof.
    """
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


class CanonicalizationError(ValueError):
    """A stable rejection from a versioned artifact canonicalization profile."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


def _canonical_number_v2(value: int | float) -> str:
    """Render the portable v0.2 JSON number subset using ECMAScript layout."""
    if isinstance(value, int):
        if abs(value) > _MAX_SAFE_JSON_INTEGER:
            raise CanonicalizationError('unsafe_integer')
        return str(value)

    if not math.isfinite(value):
        raise CanonicalizationError('non_finite_number')
    if value == 0:
        return '0'
    if value.is_integer() and abs(value) > _MAX_SAFE_JSON_INTEGER:
        raise CanonicalizationError('unsafe_integer')

    rendered = repr(value).lower()
    sign = ''
    if rendered.startswith('-'):
        sign, rendered = '-', rendered[1:]
    if 'e' in rendered:
        mantissa, exponent_text = rendered.split('e', 1)
        exponent = int(exponent_text)
    else:
        mantissa, exponent = rendered, 0
    whole, separator, fraction = mantissa.partition('.')
    raw_digits = whole + fraction
    leading_zeroes = len(raw_digits) - len(raw_digits.lstrip('0'))
    digits = raw_digits.lstrip('0').rstrip('0')
    if not digits:
        return '0'
    decimal_position = len(whole) + exponent - leading_zeroes

    if 0 < decimal_position <= 21:
        if len(digits) <= decimal_position:
            return sign + digits + ('0' * (decimal_position - len(digits)))
        return sign + digits[:decimal_position] + '.' + digits[decimal_position:]
    if -6 < decimal_position <= 0:
        return sign + '0.' + ('0' * -decimal_position) + digits

    coefficient = digits if len(digits) == 1 else digits[0] + '.' + digits[1:]
    scientific_exponent = decimal_position - 1
    exponent_sign = '+' if scientific_exponent >= 0 else ''
    return sign + coefficient + 'e' + exponent_sign + str(scientific_exponent)


def _canonicalize_v2(value: Any) -> str:
    if value is None:
        return 'null'
    if value is True:
        return 'true'
    if value is False:
        return 'false'
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    if isinstance(value, (int, float)):
        return _canonical_number_v2(value)
    if isinstance(value, (list, tuple)):
        return '[' + ','.join(_canonicalize_v2(item) for item in value) + ']'
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise CanonicalizationError('non_string_object_key')
        return '{' + ','.join(
            json.dumps(key, ensure_ascii=False, separators=(',', ':')) + ':' + _canonicalize_v2(value[key])
            for key in sorted(value, key=lambda item: item.encode('utf-16be', 'surrogatepass'))
        ) + '}'
    raise CanonicalizationError('non_json_value')


def canonicalize_artifact_v2(value: Any) -> str:
    """Return v0.2 canonical JSON without changing frozen v0.1 bytes.

    v0.2 accepts finite IEEE-754 values but rejects integral values outside the
    JSON/ECMAScript safe-integer range, so Python ``int`` values cannot silently
    acquire a different JavaScript value.  It normalizes signed zero and uses
    ECMAScript's plain/scientific decimal thresholds.
    """
    return _canonicalize_v2(value)


def canonical_artifact_bytes_v2(value: Any) -> bytes:
    """Return UTF-8 bytes for the additive v0.2 canonical JSON profile."""
    return canonicalize_artifact_v2(value).encode('utf-8')


def artifact_sha256_v2(value: Any) -> str:
    """Return SHA-256 hex digest over v0.2 canonical artifact bytes."""
    return hashlib.sha256(canonical_artifact_bytes_v2(value)).hexdigest()


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
