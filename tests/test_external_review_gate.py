from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate_external_review.py"


def _artifacts(tmp_path: Path) -> tuple[Path, Path]:
    wheel = tmp_path / "candidate.whl"
    sdist = tmp_path / "candidate.tar.gz"
    wheel.write_bytes(b"wheel")
    sdist.write_bytes(b"sdist")
    return wheel, sdist


def _record(wheel: Path, sdist: Path) -> dict[str, object]:
    return {
        "schema": "sclite.external_security_review.v1",
        "release_line": "2.0.0",
        "status": "approved",
        "source_commit": "a" * 40,
        "artifact_sha256": [
            hashlib.sha256(wheel.read_bytes()).hexdigest(),
            hashlib.sha256(sdist.read_bytes()).hexdigest(),
        ],
        "reviewer": "independent-reviewer",
        "scope": ["verifier", "release-artifacts"],
        "review_date": "2026-07-11",
        "review_verdict": "approved_with_low_or_medium_findings",
        "report_sha256": "d" * 64,
        "unresolved_critical": 0,
        "unresolved_high": 0,
        "unresolved_medium": 0,
        "unresolved_low": 1,
        "accepted_findings": ["L-01"],
    }


def _run(path: Path, wheel: Path, sdist: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([
        sys.executable, str(SCRIPT), "--stable", "--record", str(path),
        "--source-commit", "a" * 40, "--release-line", "2.0.0",
        "--artifact", str(wheel), "--artifact", str(sdist),
    ], cwd=ROOT, text=True, capture_output=True)


def test_stable_release_rejects_pending_external_review() -> None:
    result = subprocess.run([sys.executable, str(SCRIPT), "--stable"], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 1
    assert "external_review_not_approved" in result.stdout
    assert "external_review_binding_missing:source_commit" in result.stdout


def test_stable_release_accepts_complete_bound_record(tmp_path: Path) -> None:
    wheel, sdist = _artifacts(tmp_path)
    path = tmp_path / "review.json"
    path.write_text(json.dumps(_record(wheel, sdist)), encoding="utf-8")
    assert _run(path, wheel, sdist).returncode == 0


def test_stable_release_rejects_duplicate_review_keys(tmp_path: Path) -> None:
    wheel, sdist = _artifacts(tmp_path)
    payload = json.dumps(_record(wheel, sdist))
    payload = payload[:-1] + ', "unresolved_high": 0}'
    path = tmp_path / "review.json"
    path.write_text(payload, encoding="utf-8")
    result = _run(path, wheel, sdist)
    assert result.returncode == 1
    assert "external_review_duplicate_key:unresolved_high" in result.stdout


@pytest.mark.parametrize("field", ["unresolved_critical", "unresolved_high", "unresolved_medium", "unresolved_low"])
def test_stable_release_rejects_missing_finding_counts(tmp_path: Path, field: str) -> None:
    wheel, sdist = _artifacts(tmp_path)
    record = _record(wheel, sdist)
    record.pop(field)
    path = tmp_path / "review.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    result = _run(path, wheel, sdist)
    assert result.returncode == 1
    assert f"external_review_missing:{field}" in result.stdout


@pytest.mark.parametrize("value", ["0", False, -1, 1.5])
def test_stable_release_rejects_invalid_finding_counts(tmp_path: Path, value: object) -> None:
    wheel, sdist = _artifacts(tmp_path)
    record = _record(wheel, sdist)
    record["unresolved_medium"] = value
    path = tmp_path / "review.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    assert _run(path, wheel, sdist).returncode == 1


@pytest.mark.parametrize("scope", ["verifier", [], [""], ["same", "same"]])
def test_stable_release_rejects_invalid_scope_type(tmp_path: Path, scope: object) -> None:
    wheel, sdist = _artifacts(tmp_path)
    record = _record(wheel, sdist)
    record["scope"] = scope
    path = tmp_path / "review.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    result = _run(path, wheel, sdist)
    assert result.returncode == 1
    assert "external_review_scope" in result.stdout


def test_stable_release_rejects_duplicate_artifact_hashes(tmp_path: Path) -> None:
    wheel, sdist = _artifacts(tmp_path)
    record = _record(wheel, sdist)
    record["artifact_sha256"] = ["b" * 64, "b" * 64]
    path = tmp_path / "review.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    result = _run(path, wheel, sdist)
    assert result.returncode == 1
    assert "external_review_artifact_sha256_format" in result.stdout


def test_stable_release_rejects_unknown_field(tmp_path: Path) -> None:
    wheel, sdist = _artifacts(tmp_path)
    record = _record(wheel, sdist)
    record["approval_override"] = True
    path = tmp_path / "review.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    result = _run(path, wheel, sdist)
    assert result.returncode == 1
    assert "external_review_unknown_field:approval_override" in result.stdout


@pytest.mark.parametrize(("medium", "low", "accepted"), [
    (1, 0, []),
    (0, 1, ["L-01"]),
])
def test_review_approved_requires_zero_findings(
    tmp_path: Path,
    medium: int,
    low: int,
    accepted: list[str],
) -> None:
    wheel, sdist = _artifacts(tmp_path)
    record = _record(wheel, sdist)
    record.update({
        "review_verdict": "approved",
        "unresolved_medium": medium,
        "unresolved_low": low,
        "accepted_findings": accepted,
    })
    path = tmp_path / "review.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    result = _run(path, wheel, sdist)
    assert result.returncode == 1
    assert "external_review_approved_requires_zero_findings" in result.stdout


@pytest.mark.parametrize(("medium", "low", "accepted"), [
    (0, 0, []),
    (1, 1, ["M-01"]),
    (0, 1, []),
])
def test_review_approved_with_findings_requires_matching_accepted_ids(
    tmp_path: Path,
    medium: int,
    low: int,
    accepted: list[str],
) -> None:
    wheel, sdist = _artifacts(tmp_path)
    record = _record(wheel, sdist)
    record.update({
        "unresolved_medium": medium,
        "unresolved_low": low,
        "accepted_findings": accepted,
    })
    path = tmp_path / "review.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    result = _run(path, wheel, sdist)
    assert result.returncode == 1
    assert "external_review_accepted_findings_mismatch" in result.stdout
