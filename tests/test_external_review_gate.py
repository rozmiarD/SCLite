from __future__ import annotations

import json
import hashlib
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
    assert "external_review_binding_missing:source_commit" in result.stdout


def test_stable_release_accepts_complete_zero_findings_record(tmp_path: Path) -> None:
    wheel = tmp_path / 'candidate.whl'
    sdist = tmp_path / 'candidate.tar.gz'
    wheel.write_bytes(b'wheel')
    sdist.write_bytes(b'sdist')
    record = {
        "schema": "sclite.external_security_review.v1",
        "release_line": "2.0.0rc1",
        "status": "approved",
        "source_commit": "a" * 40,
        "artifact_sha256": [hashlib.sha256(wheel.read_bytes()).hexdigest(), hashlib.sha256(sdist.read_bytes()).hexdigest()],
        "reviewer": "independent-reviewer",
        "scope": ["verifier"],
        "unresolved_high": 0,
        "unresolved_critical": 0,
    }
    path = tmp_path / "review.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--stable", "--record", str(path), "--source-commit", "a" * 40, "--release-line", "2.0.0rc1", "--artifact", str(wheel), "--artifact", str(sdist)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0


def test_stable_release_rejects_missing_binding_arguments(tmp_path: Path) -> None:
    record = {"schema": "sclite.external_security_review.v1", "release_line": "2.0.0", "status": "approved", "source_commit": "a" * 40, "artifact_sha256": ["b" * 64, "c" * 64], "reviewer": "reviewer", "scope": ["verifier"], "unresolved_high": 0, "unresolved_critical": 0}
    path = tmp_path / 'review.json'
    path.write_text(json.dumps(record), encoding='utf-8')
    result = subprocess.run([sys.executable, str(SCRIPT), '--stable', '--record', str(path)], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 1
    assert 'binding_missing:source_commit' in result.stdout
    assert 'binding_requires_two_artifacts' in result.stdout


def test_stable_release_rejects_bound_value_mismatch(tmp_path: Path) -> None:
    artifact = tmp_path / 'candidate.whl'
    second_artifact = tmp_path / 'candidate.tar.gz'
    artifact.write_bytes(b'candidate')
    second_artifact.write_bytes(b'candidate-sdist')
    record = {"schema": "sclite.external_security_review.v1", "release_line": "2.0.0", "status": "approved", "source_commit": "a" * 40, "artifact_sha256": ["b" * 64, "c" * 64], "reviewer": "reviewer", "scope": ["verifier"], "unresolved_high": 0, "unresolved_critical": 0}
    path = tmp_path / 'review.json'
    path.write_text(json.dumps(record), encoding='utf-8')
    result = subprocess.run([sys.executable, str(SCRIPT), '--stable', '--record', str(path), '--source-commit', 'd' * 40, '--release-line', '2.0.1', '--artifact', str(artifact), '--artifact', str(second_artifact)], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 1
    assert 'source_commit_mismatch' in result.stdout
    assert 'release_line_mismatch' in result.stdout
    assert 'artifact_sha256_mismatch' in result.stdout
