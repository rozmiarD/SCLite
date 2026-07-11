from __future__ import annotations

import json
import subprocess
import sys

import pytest

from sclite import ImmutableSchemaResolver, SchemaResolutionError, verify_artifact


DOMAIN_SCHEMA = {
    "type": "object",
    "required": ["artifact_type"],
    "properties": {"artifact_type": {"const": "example"}},
    "additionalProperties": False,
}


def test_host_supplied_domain_schema_needs_no_global_registration() -> None:
    resolver = ImmutableSchemaResolver({"example.org/example@v1": DOMAIN_SCHEMA})
    result = verify_artifact(
        {"artifact_type": "example"}, schema_ref="example.org/example@v1", resolver=resolver
    )
    assert result.status == "pass"
    assert resolver.inventory()[0].schema_ref == "example.org/example@v1"


def test_resolution_is_copy_safe_and_resolver_is_immutable() -> None:
    resolver = ImmutableSchemaResolver({"example.org/example@v1": DOMAIN_SCHEMA})
    first = resolver.resolve("example.org/example@v1")
    first["type"] = "array"
    assert resolver.resolve("example.org/example@v1")["type"] == "object"
    with pytest.raises(AttributeError, match="immutable"):
        resolver.extra = True  # type: ignore[attr-defined]


def test_namespace_validation_unknown_ref_and_collision() -> None:
    with pytest.raises(SchemaResolutionError, match="namespaced"):
        ImmutableSchemaResolver({"example": DOMAIN_SCHEMA})
    resolver = ImmutableSchemaResolver({"example.org/example@v1": DOMAIN_SCHEMA})
    with pytest.raises(SchemaResolutionError, match="unknown"):
        resolver.resolve("other.org/example@v1")
    with pytest.raises(SchemaResolutionError, match="collision"):
        ImmutableSchemaResolver.combine(
            {"example.org/example@v1": DOMAIN_SCHEMA},
            {"example.org/example@v1": {"type": "array"}},
        )


def test_inventory_is_identical_in_fresh_process() -> None:
    expected = ImmutableSchemaResolver({"example.org/example@v1": DOMAIN_SCHEMA}).inventory()[0]
    code = (
        "import json; from sclite import ImmutableSchemaResolver; "
        f"r=ImmutableSchemaResolver(json.loads({json.dumps(json.dumps({'example.org/example@v1': DOMAIN_SCHEMA}))})); "
        "e=r.inventory()[0]; print(e.sha256, e.canonical_bytes)"
    )
    proc = subprocess.run([sys.executable, "-c", code], text=True, capture_output=True, check=True)
    assert proc.stdout.strip() == f"{expected.sha256} {expected.canonical_bytes}"
