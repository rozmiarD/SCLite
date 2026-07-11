from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


FIELDS = {
    "schema", "release_line", "status", "source_commit", "artifact_sha256",
    "reviewer", "scope", "review_date", "review_verdict", "report_sha256",
    "unresolved_critical", "unresolved_high", "unresolved_medium",
    "unresolved_low", "accepted_findings",
}
VERDICTS = {"approved", "approved_with_low_or_medium_findings"}


class DuplicateKeyError(ValueError):
    pass


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(key)
        result[key] = value
    return result


def _load(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)
    except DuplicateKeyError as exc:
        return None, [f"external_review_duplicate_key:{exc.args[0]}"]
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, [f"external_review_invalid_json:{type(exc).__name__}"]
    if not isinstance(value, dict):
        return None, ["external_review_root_type"]
    return value, []


def _string_list(record: dict[str, Any], field: str, *, nonempty: bool) -> bool:
    value = record.get(field)
    return isinstance(value, list) and (not nonempty or bool(value)) and all(
        isinstance(item, str) and bool(item.strip()) for item in value
    ) and len(value) == len(set(value))


def _count(record: dict[str, Any], field: str, errors: list[str]) -> int | None:
    value = record.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        errors.append(f"external_review_invalid_count:{field}")
        return None
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stable", action="store_true")
    parser.add_argument("--record", type=Path, default=Path("security/EXTERNAL_REVIEW.json"))
    parser.add_argument("--source-commit")
    parser.add_argument("--release-line")
    parser.add_argument("--artifact", action="append", type=Path, default=[])
    args = parser.parse_args()
    record, errors = _load(args.record)
    if record is None:
        print("\n".join(errors))
        return 1

    unknown = sorted(set(record) - FIELDS)
    missing = sorted(FIELDS - set(record))
    errors.extend(f"external_review_unknown_field:{field}" for field in unknown)
    errors.extend(f"external_review_missing:{field}" for field in missing)
    if record.get("schema") != "sclite.external_security_review.v1":
        errors.append("external_review_schema")
    counts = {field: _count(record, field, errors) for field in (
        "unresolved_critical", "unresolved_high", "unresolved_medium", "unresolved_low"
    )}
    if counts["unresolved_high"] not in {None, 0} or counts["unresolved_critical"] not in {None, 0}:
        errors.append("external_review_high_or_critical_open")

    if args.stable:
        if not args.source_commit:
            errors.append("external_review_binding_missing:source_commit")
        if not args.release_line:
            errors.append("external_review_binding_missing:release_line")
        if len(args.artifact) != 2:
            errors.append("external_review_binding_requires_two_artifacts")
        if record.get("status") != "approved":
            errors.append("external_review_not_approved")
        source_commit = record.get("source_commit")
        if not isinstance(source_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
            errors.append("external_review_source_commit_format")
        if args.source_commit and source_commit != args.source_commit:
            errors.append("external_review_source_commit_mismatch")
        if not isinstance(record.get("release_line"), str) or record.get("release_line") != args.release_line:
            errors.append("external_review_release_line_mismatch")
        hashes = record.get("artifact_sha256")
        if not _string_list(record, "artifact_sha256", nonempty=True) or len(hashes) != 2 or any(
            not re.fullmatch(r"[0-9a-f]{64}", item) for item in hashes
        ):
            errors.append("external_review_artifact_sha256_format")
        if not isinstance(record.get("reviewer"), str) or not record["reviewer"].strip():
            errors.append("external_review_reviewer")
        if not _string_list(record, "scope", nonempty=True):
            errors.append("external_review_scope")
        if not _string_list(record, "accepted_findings", nonempty=False):
            errors.append("external_review_accepted_findings")
        if not isinstance(record.get("review_date"), str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", record["review_date"]):
            errors.append("external_review_date")
        if record.get("review_verdict") not in VERDICTS:
            errors.append("external_review_verdict")
        accepted_findings = record.get("accepted_findings")
        medium = counts["unresolved_medium"]
        low = counts["unresolved_low"]
        if record.get("review_verdict") == "approved" and (
            medium not in {None, 0}
            or low not in {None, 0}
            or accepted_findings not in (None, [])
        ):
            errors.append("external_review_approved_requires_zero_findings")
        if (
            record.get("review_verdict") == "approved_with_low_or_medium_findings"
            and medium is not None
            and low is not None
            and isinstance(accepted_findings, list)
            and (
                medium + low == 0
                or not accepted_findings
                or len(accepted_findings) != medium + low
            )
        ):
            errors.append("external_review_accepted_findings_mismatch")
        report_hash = record.get("report_sha256")
        if not isinstance(report_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", report_hash):
            errors.append("external_review_report_sha256")
        if len(args.artifact) == 2 and isinstance(hashes, list):
            actual = sorted(hashlib.sha256(path.read_bytes()).hexdigest() for path in args.artifact)
            if sorted(hashes) != actual:
                errors.append("external_review_artifact_sha256_mismatch")
    if errors:
        print("\n".join(dict.fromkeys(errors)))
        return 1
    print(f"external_review_gate_ok:{record.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
