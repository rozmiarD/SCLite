from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stable", action="store_true")
    parser.add_argument("--record", type=Path, default=Path("security/EXTERNAL_REVIEW.json"))
    parser.add_argument("--source-commit")
    parser.add_argument("--release-line")
    parser.add_argument("--artifact", action="append", type=Path, default=[])
    args = parser.parse_args()
    record = json.loads(args.record.read_text(encoding="utf-8"))
    errors: list[str] = []
    if record.get("schema") != "sclite.external_security_review.v1":
        errors.append("external_review_schema")
    if int(record.get("unresolved_high", 0)) or int(record.get("unresolved_critical", 0)):
        errors.append("external_review_high_or_critical_open")
    if args.stable:
        if not args.source_commit:
            errors.append("external_review_binding_missing:source_commit")
        if not args.release_line:
            errors.append("external_review_binding_missing:release_line")
        if len(args.artifact) != 2:
            errors.append("external_review_binding_requires_two_artifacts")
        for field in ("source_commit", "artifact_sha256", "reviewer", "scope"):
            if not record.get(field):
                errors.append(f"external_review_missing:{field}")
        if record.get("status") != "approved":
            errors.append("external_review_not_approved")
        source_commit = str(record.get("source_commit") or "")
        if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
            errors.append("external_review_source_commit_format")
        hashes = record.get("artifact_sha256")
        if not isinstance(hashes, list) or len(hashes) != 2 or any(not re.fullmatch(r"[0-9a-f]{64}", str(item)) for item in hashes):
            errors.append("external_review_artifact_sha256_format")
        if args.source_commit and source_commit != args.source_commit:
            errors.append("external_review_source_commit_mismatch")
        if args.release_line and record.get("release_line") != args.release_line:
            errors.append("external_review_release_line_mismatch")
        if len(args.artifact) == 2:
            actual = sorted(hashlib.sha256(path.read_bytes()).hexdigest() for path in args.artifact)
            if sorted(str(item) for item in hashes or []) != actual:
                errors.append("external_review_artifact_sha256_mismatch")
    if errors:
        print("\n".join(errors))
        return 1
    print(f"external_review_gate_ok:{record.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
