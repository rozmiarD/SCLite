from __future__ import annotations

from collections.abc import Mapping as MappingABC
from typing import Any, Mapping, TypeAlias

JsonScalar: TypeAlias = str | int | float | bool | None
JsonObject: TypeAlias = dict[str, Any]
JsonArray: TypeAlias = list[Any]
JsonMapping: TypeAlias = Mapping[str, Any]


def json_mapping(value: Any) -> JsonMapping:
    """Return a read-only JSON object view or an empty mapping."""
    if isinstance(value, MappingABC):
        return value
    return {}


def json_object(value: Any, *, label: str = 'value') -> JsonObject:
    """Return a mutable JSON object, failing when the value is not object-shaped."""
    if not isinstance(value, dict):
        raise TypeError(f'{label} must be a JSON object')
    return value


def json_array(value: Any) -> JsonArray:
    """Return a JSON array or an empty array."""
    if isinstance(value, list):
        return value
    return []
