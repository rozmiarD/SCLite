from __future__ import annotations

from pathlib import Path

import sclite
from sclite import consumer_contracts


def test_public_export_inventory_is_complete_and_classified() -> None:
    assert consumer_contracts.validate_public_export_inventory(sclite.__all__) == []
    records = consumer_contracts.load_consumer_import_inventory()["public_exports"]
    assert {record["classification"] for record in records.values()} == {
        "stable",
        "bridge",
        "testing",
        "internal",
    }
    assert all(record["owner"] and record["disposition"] for record in records.values())


def test_every_allowed_consumer_symbol_imports() -> None:
    assert consumer_contracts.validate_allowed_imports_load() == []


def test_new_deep_import_fails_consumer_contract(tmp_path: Path, monkeypatch) -> None:
    source_root = tmp_path / "src" / "consumer"
    source_root.mkdir(parents=True)
    (source_root / "module.py").write_text(
        "from sclite.integrity.chain import ChainVerificationError\n"
        "from sclite.secure import verify_secure_bundle\n",
        encoding="utf-8",
    )
    inventory = {
        "schema": consumer_contracts.INVENTORY_SCHEMA,
        "consumers": {
            "fixture": {
                "source_roots": ["src/consumer"],
                "imports": {
                    "sclite.integrity.chain": ["ChainVerificationError"],
                },
            }
        },
    }
    monkeypatch.setattr(consumer_contracts, "load_consumer_import_inventory", lambda: inventory)

    assert consumer_contracts.validate_consumer_imports("fixture", tmp_path) == [
        "consumer_import_new_module:fixture:sclite.secure"
    ]


def test_removed_import_fails_as_stale_contract(tmp_path: Path, monkeypatch) -> None:
    source_root = tmp_path / "consumer"
    source_root.mkdir()
    (source_root / "module.py").write_text(
        "from sclite.integrity import artifact_descriptor\n",
        encoding="utf-8",
    )
    inventory = {
        "schema": consumer_contracts.INVENTORY_SCHEMA,
        "consumers": {
            "fixture": {
                "source_roots": ["consumer"],
                "imports": {
                    "sclite.integrity": [
                        "artifact_descriptor",
                        "verify_lifecycle_manifest",
                    ],
                },
            }
        },
    }
    monkeypatch.setattr(consumer_contracts, "load_consumer_import_inventory", lambda: inventory)

    assert consumer_contracts.validate_consumer_imports("fixture", tmp_path) == [
        "consumer_import_stale_symbol:fixture:sclite.integrity:verify_lifecycle_manifest"
    ]
