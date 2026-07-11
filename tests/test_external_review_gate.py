from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate_external_review.py"


def test_stable_release_rejects_pending_external_review() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--stable"], cwd=ROOT, text=True, capture_output=True
    )
    assert result.returncode == 1
    assert "external_review_not_approved" in result.stdout


def test_stable_release_accepts_complete_zero_findings_record(tmp_path: Path) -> None:
    record = {
        "schema": "sclite.external_security_review.v1",
        "release_line": "2.0.0rc1",
        "status": "approved",
        "source_commit": "a" * 40,
        "artifact_sha256": ["b" * 64, "c" * 64],
        "reviewer": "independent-reviewer",
        "scope": ["verifier"],
        "unresolved_high": 0,
        "unresolved_critical": 0,
    }
    path = tmp_path / "review.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--stable", "--record", str(path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0


def test_stable_release_rejects_bound_value_mismatch(tmp_path: Path) -> None:
    artifact = tmp_path / 'candidate.whl'
    artifact.write_bytes(b'candidate')
    record = {"schema": "sclite.external_security_review.v1", "release_line": "2.0.0", "status": "approved", "source_commit": "a" * 40, "artifact_sha256": ["b" * 64, "c" * 64], "reviewer": "reviewer", "scope": ["verifier"], "unresolved_high": 0, "unresolved_critical": 0}
    path = tmp_path / 'review.json'
    path.write_text(json.dumps(record), encoding='utf-8')
    result = subprocess.run([sys.executable, str(SCRIPT), '--stable', '--record', str(path), '--source-commit', 'd' * 40, '--release-line', '2.0.1', '--artifact', str(artifact)], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 1
    assert 'source_commit_mismatch' in result.stdout
    assert 'release_line_mismatch' in result.stdout
    assert 'artifact_sha256_mismatch' in result.stdout
