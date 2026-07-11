from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stable", action="store_true")
    parser.add_argument("--record", type=Path, default=Path("security/EXTERNAL_REVIEW.json"))
    args = parser.parse_args()
    record = json.loads(args.record.read_text(encoding="utf-8"))
    errors: list[str] = []
    if record.get("schema") != "sclite.external_security_review.v1":
        errors.append("external_review_schema")
    if int(record.get("unresolved_high", 0)) or int(record.get("unresolved_critical", 0)):
        errors.append("external_review_high_or_critical_open")
    if args.stable:
        for field in ("source_commit", "artifact_sha256", "reviewer", "scope"):
            if not record.get(field):
                errors.append(f"external_review_missing:{field}")
        if record.get("status") != "approved":
            errors.append("external_review_not_approved")
    if errors:
        print("\n".join(errors))
        return 1
    print(f"external_review_gate_ok:{record.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
