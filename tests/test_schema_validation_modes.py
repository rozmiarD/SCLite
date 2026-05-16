from __future__ import annotations

import pytest

from sclite.artifacts import validate_json_schema_value


jsonschema = pytest.importorskip('jsonschema')


def test_dependency_free_schema_validator_is_documented_subset() -> None:
    schema = {
        'type': 'object',
        'required': ['slug'],
        'properties': {
            'slug': {
                'type': 'string',
                'pattern': '^[a-z0-9-]+$',
                'maxLength': 8,
            }
        },
        'additionalProperties': False,
    }
    value = {'slug': 'NOT A VALID LONG SLUG'}

    # The dependency-free validator intentionally ignores pattern/maxLength.
    validate_json_schema_value(schema, value)

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(value)
