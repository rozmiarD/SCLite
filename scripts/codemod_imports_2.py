from __future__ import annotations

import argparse
from pathlib import Path


MODULE_REPLACEMENTS = {
    "sclite.automation": "rexecop.contracts.automation",
    "sclite.reactions": "rexecop.contracts.reactions",
    "sclite.triggers": "rexecop.contracts.triggers",
    "sclite.watchdog": "rexecop.contracts.watchdog",
}


def migrate(text: str) -> str:
    for old, new in MODULE_REPLACEMENTS.items():
        text = text.replace(f"from {old} import", f"from {new} import")
        text = text.replace(f"import {old}", f"import {new}")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Rewrite SCLite 1.x owner-module imports")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changed: list[Path] = []
    for path in args.paths:
        original = path.read_text(encoding="utf-8")
        updated = migrate(original)
        if updated != original:
            changed.append(path)
            if not args.check:
                path.write_text(updated, encoding="utf-8")
    for path in changed:
        print(path)
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
