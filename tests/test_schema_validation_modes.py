from __future__ import annotations

import pytest

from sclite.artifacts import JsonSchemaValidationError, validate_json_schema_value


jsonschema = pytest.importorskip('jsonschema')


def test_dependency_free_schema_validator_enforces_selected_release_keywords() -> None:
    schema = {
        'type': 'object',
        'required': ['slug', 'items'],
        'properties': {
            'slug': {
                'type': 'string',
                'pattern': '^[a-z0-9-]+$',
                'maxLength': 8,
            },
            'items': {'type': 'array', 'minItems': 1, 'items': {'type': 'string'}},
        },
        'additionalProperties': False,
    }
    value = {'slug': 'NOT A VALID LONG SLUG', 'items': []}

    with pytest.raises(JsonSchemaValidationError, match='maxLength|pattern|minItems'):
        validate_json_schema_value(schema, value)

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(value)


def test_dependency_free_schema_validator_resolves_local_refs() -> None:
    schema = {
        'type': 'object',
        'required': ['link'],
        'properties': {
            'link': {'$ref': '#/$defs/link'},
        },
        '$defs': {
            'link': {
                'type': 'object',
                'required': ['digest'],
                'properties': {
                    'digest': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'},
                },
                'additionalProperties': False,
            },
        },
    }

    validate_json_schema_value(schema, {'link': {'digest': 'a' * 64}})
    with pytest.raises(JsonSchemaValidationError, match='pattern'):
        validate_json_schema_value(schema, {'link': {'digest': 'not-a-digest'}})
