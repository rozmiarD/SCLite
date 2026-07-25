from __future__ import annotations

import argparse
import ast
import importlib
import json
from collections.abc import Mapping, Sequence
from importlib.resources import files
from pathlib import Path
from typing import Any

INVENTORY_SCHEMA = "sclite.consumer_import_inventory.v1"
INVENTORY_VERSION_LINE = "2.0.x"
EXPORT_DISPOSITIONS = frozenset({"retain_2.x", "internal_compatibility_2.x"})


def load_consumer_import_inventory() -> dict[str, Any]:
    resource = files("sclite.contracts").joinpath("consumer_imports.v1.json")
    value = json.loads(resource.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != INVENTORY_SCHEMA:
        raise ValueError("invalid SCLite consumer import inventory")
    return value


def validate_public_export_inventory(exports: Sequence[str]) -> list[str]:
    inventory = load_consumer_import_inventory()
    records = inventory.get("public_exports")
    if not isinstance(records, Mapping):
        return ["consumer_inventory_missing_public_exports"]
    errors: list[str] = []
    if inventory.get("sclite_version_line") != INVENTORY_VERSION_LINE:
        errors.append(
            "consumer_inventory_version_line_mismatch:"
            f"{inventory.get('sclite_version_line')}!={INVENTORY_VERSION_LINE}"
        )
    expected = set(exports)
    recorded = {str(name) for name in records}
    for name in sorted(expected - recorded):
        errors.append(f"consumer_inventory_missing_export:{name}")
    for name in sorted(recorded - expected):
        errors.append(f"consumer_inventory_retired_export:{name}")
    for name, record in records.items():
        if not isinstance(record, Mapping):
            errors.append(f"consumer_inventory_invalid_export_record:{name}")
            continue
        if record.get("classification") not in {"stable", "bridge", "testing", "internal"}:
            errors.append(f"consumer_inventory_invalid_classification:{name}")
        if not str(record.get("owner") or ""):
            errors.append(f"consumer_inventory_missing_owner:{name}")
        disposition = str(record.get("disposition") or "")
        if not disposition:
            errors.append(f"consumer_inventory_missing_disposition:{name}")
        elif disposition not in EXPORT_DISPOSITIONS:
            errors.append(f"consumer_inventory_invalid_disposition:{name}:{disposition}")
    return errors


def validate_consumer_imports(consumer: str, repo_root: str | Path) -> list[str]:
    consumers = load_consumer_import_inventory().get("consumers")
    if not isinstance(consumers, Mapping) or consumer not in consumers:
        return [f"consumer_import_inventory_unknown_consumer:{consumer}"]
    contract = consumers[consumer]
    if not isinstance(contract, Mapping):
        return [f"consumer_import_inventory_invalid_contract:{consumer}"]
    allowed_raw = contract.get("imports")
    roots_raw = contract.get("source_roots")
    if not isinstance(allowed_raw, Mapping) or not isinstance(roots_raw, list):
        return [f"consumer_import_inventory_invalid_contract:{consumer}"]
    allowed = {
        str(module): {str(symbol) for symbol in symbols}
        for module, symbols in allowed_raw.items()
        if isinstance(symbols, list)
    }
    actual: dict[str, set[str]] = {}
    root = Path(repo_root)
    for source_root in roots_raw:
        path = root / str(source_root)
        if not path.is_dir():
            return [f"consumer_import_source_root_missing:{consumer}:{source_root}"]
        for source in sorted(path.rglob("*.py")):
            _collect_sclite_imports(source, actual)
    errors: list[str] = []
    for module, symbols in sorted(actual.items()):
        if module not in allowed:
            errors.append(f"consumer_import_new_module:{consumer}:{module}")
            continue
        for symbol in sorted(symbols - allowed[module]):
            errors.append(f"consumer_import_new_symbol:{consumer}:{module}:{symbol}")
    for module, symbols in sorted(allowed.items()):
        if module not in actual:
            errors.append(f"consumer_import_stale_module:{consumer}:{module}")
            continue
        for symbol in sorted(symbols - actual[module]):
            errors.append(f"consumer_import_stale_symbol:{consumer}:{module}:{symbol}")
    return errors


def validate_allowed_imports_load(consumer: str | None = None) -> list[str]:
    consumers = load_consumer_import_inventory().get("consumers")
    if not isinstance(consumers, Mapping):
        return ["consumer_import_inventory_missing_consumers"]
    names = [consumer] if consumer else sorted(str(name) for name in consumers)
    errors: list[str] = []
    for name in names:
        contract = consumers.get(name)
        if not isinstance(contract, Mapping) or not isinstance(contract.get("imports"), Mapping):
            errors.append(f"consumer_import_inventory_invalid_contract:{name}")
            continue
        imports = contract["imports"]
        assert isinstance(imports, Mapping)
        for module_name, symbols in imports.items():
            try:
                module = importlib.import_module(str(module_name))
            except ImportError as exc:
                errors.append(f"consumer_import_module_unavailable:{name}:{module_name}:{exc}")
                continue
            if not isinstance(symbols, list):
                errors.append(f"consumer_import_inventory_invalid_symbols:{name}:{module_name}")
                continue
            for symbol in symbols:
                if not hasattr(module, str(symbol)):
                    errors.append(f"consumer_import_symbol_unavailable:{name}:{module_name}:{symbol}")
    return errors


def _collect_sclite_imports(source: Path, output: dict[str, set[str]]) -> None:
    try:
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    except (OSError, SyntaxError) as exc:
        raise ValueError(f"cannot parse consumer source: {source}: {exc}") from exc
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and _is_sclite_module(node.module):
            output.setdefault(node.module, set()).update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if _is_sclite_module(alias.name):
                    output.setdefault(alias.name, set()).add("*module*")


def _is_sclite_module(name: str) -> bool:
    return name == "sclite" or name.startswith("sclite.")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate frozen SCLite consumer imports")
    parser.add_argument("--consumer", choices=("govengine", "rexecop", "tecrax"))
    parser.add_argument("--repo")
    parser.add_argument("--imports-only", action="store_true")
    args = parser.parse_args(argv)
    if args.imports_only:
        errors = validate_allowed_imports_load(args.consumer)
    elif args.consumer and args.repo:
        errors = validate_consumer_imports(args.consumer, args.repo)
    else:
        parser.error("use --imports-only or provide --consumer and --repo")
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"consumer_import_contract_ok:{args.consumer or 'all'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
