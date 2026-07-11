from __future__ import annotations

import importlib.util
import warnings

import pytest


REMOVED_MODULES = (
    "sclite.reactions",
    "sclite.triggers",
    "sclite.watchdog",
    "sclite.automation",
)


def test_stack_specific_modules_and_schemas_are_not_packaged() -> None:
    assert all(importlib.util.find_spec(name) is None for name in REMOVED_MODULES)


def test_supported_suite_emits_no_deprecation_warnings() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        import sclite

        resolver = sclite.ImmutableSchemaResolver(
            {"example.org/artifact@v1": {"type": "object", "additionalProperties": True}}
        )
        sclite.verify_artifact({}, schema_ref="example.org/artifact@v1", resolver=resolver)


@pytest.mark.parametrize("name", ("build_trigger_decision", "legacy_public_safe"))
def test_removed_top_level_aliases_are_absent(name: str) -> None:
    import sclite

    assert not hasattr(sclite, name)
