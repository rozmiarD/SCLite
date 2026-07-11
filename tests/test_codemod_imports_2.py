from __future__ import annotations

from scripts.codemod_imports_2 import migrate


def test_owner_module_import_codemod() -> None:
    assert migrate("from sclite.triggers import build_trigger_decision\n") == (
        "from rexecop.contracts.triggers import build_trigger_decision\n"
    )
