from __future__ import annotations

import pytest

from sclite.artifacts import load_json_schema


def test_stack_specific_builtin_directs_hosts_to_owner_resolver() -> None:
    with pytest.deprecated_call(match="owner contract resolver"):
        load_json_schema("trigger_decision.v0.1")
