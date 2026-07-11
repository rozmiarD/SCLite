from __future__ import annotations

import argparse
import ast
from pathlib import Path


FORBIDDEN_MODULES = {
    "sclite.reactions",
    "sclite.triggers",
    "sclite.watchdog",
    "sclite.automation",
    "sclite.hosts",
    "sclite.redaction",
}
FORBIDDEN_ROOT_SYMBOLS = {
    "build_observation_envelope",
    "build_finding",
    "build_reaction_plan",
    "build_trigger_decision",
    "build_watchdog_decision",
    "build_automation_chain",
    "validate_escalation_proposal",
    "legacy_public_safe",
}


def scan(repo: Path) -> list[str]:
    errors: list[str] = []
    for source in sorted((repo / "src").rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module in FORBIDDEN_MODULES:
                    errors.append(f"forbidden_module:{source.relative_to(repo)}:{node.module}")
                if node.module == "sclite":
                    for alias in node.names:
                        if alias.name in FORBIDDEN_ROOT_SYMBOLS:
                            errors.append(
                                f"forbidden_symbol:{source.relative_to(repo)}:{alias.name}"
                            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repos", nargs="+", type=Path)
    args = parser.parse_args()
    errors = [error for repo in args.repos for error in scan(repo.resolve())]
    if errors:
        print("\n".join(errors))
        return 1
    print("forbidden_consumer_imports_ok:" + ",".join(repo.name for repo in args.repos))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
