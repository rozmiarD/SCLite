from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Protocol, runtime_checkable


SCHEMA_IDENTIFIER_PATTERN = re.compile(
    r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*/[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*@v[0-9]+(?:\.[0-9]+)*$"
)


class SchemaResolutionError(ValueError):
    """An explicit schema contract set is invalid or cannot resolve a reference."""


@dataclass(frozen=True, slots=True)
class SchemaInventoryEntry:
    schema_ref: str
    sha256: str
    canonical_bytes: int


@runtime_checkable
class SchemaResolver(Protocol):
    """Read-only, offline schema resolver supplied explicitly by a host."""

    def resolve(self, schema_ref: str) -> Mapping[str, Any]: ...

    def inventory(self) -> tuple[SchemaInventoryEntry, ...]: ...


class ImmutableSchemaResolver:
    """Deterministic resolver backed by canonical JSON bytes, with no discovery or I/O."""

    __slots__ = ("_schemas", "_inventory", "_frozen")
    _schemas: Mapping[str, bytes]
    _inventory: tuple[SchemaInventoryEntry, ...]
    _frozen: bool

    def __init__(self, schemas: Mapping[str, Mapping[str, Any]]) -> None:
        encoded: dict[str, bytes] = {}
        for schema_ref, schema in schemas.items():
            ref = str(schema_ref)
            if SCHEMA_IDENTIFIER_PATTERN.fullmatch(ref) is None:
                raise SchemaResolutionError(f"{ref!r}: expected namespaced schema identifier namespace/name@vN")
            canonical = json.dumps(
                schema, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            ).encode("utf-8")
            previous = encoded.get(ref)
            if previous is not None and previous != canonical:
                raise SchemaResolutionError(f"{ref}: conflicting schema definitions")
            encoded[ref] = canonical
        object.__setattr__(self, "_schemas", MappingProxyType(dict(sorted(encoded.items()))))
        object.__setattr__(
            self,
            "_inventory",
            tuple(
                SchemaInventoryEntry(ref, hashlib.sha256(payload).hexdigest(), len(payload))
                for ref, payload in sorted(encoded.items())
            ),
        )
        object.__setattr__(self, "_frozen", True)

    @classmethod
    def combine(cls, *contract_sets: Mapping[str, Mapping[str, Any]]) -> ImmutableSchemaResolver:
        combined: dict[str, Mapping[str, Any]] = {}
        fingerprints: dict[str, bytes] = {}
        for contract_set in contract_sets:
            for ref, schema in contract_set.items():
                canonical = json.dumps(
                    schema, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
                ).encode("utf-8")
                if ref in fingerprints and fingerprints[ref] != canonical:
                    raise SchemaResolutionError(f"{ref}: collision between contract sets")
                fingerprints[ref] = canonical
                combined[ref] = schema
        return cls(combined)

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_frozen", False):
            raise AttributeError("ImmutableSchemaResolver is immutable")
        object.__setattr__(self, name, value)

    def resolve(self, schema_ref: str) -> Mapping[str, Any]:
        try:
            payload = self._schemas[schema_ref]
        except KeyError as exc:
            raise SchemaResolutionError(f"{schema_ref}: unknown namespaced schema") from exc
        value = json.loads(payload)
        if not isinstance(value, dict):  # construction already receives mappings; defensive invariant
            raise SchemaResolutionError(f"{schema_ref}: schema must be an object")
        return value

    def inventory(self) -> tuple[SchemaInventoryEntry, ...]:
        return self._inventory
