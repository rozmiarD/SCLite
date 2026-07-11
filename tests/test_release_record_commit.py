from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.validate_release_record_commit import validate_record_commit


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def _repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.name", "test")
    _git(repo, "config", "user.email", "test@example.invalid")
    (repo / "security").mkdir()
    (repo / "source.py").write_text("SOURCE = True\n", encoding="utf-8")
    (repo / "security" / "EXTERNAL_REVIEW.json").write_text("{}\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "source")
    return repo, _git(repo, "rev-parse", "HEAD")


def test_record_only_commit_resolves_direct_source_parent(tmp_path: Path) -> None:
    repo, source = _repo(tmp_path)
    (repo / "security" / "EXTERNAL_REVIEW.json").write_text('{"status":"approved"}\n', encoding="utf-8")
    _git(repo, "add", "security/EXTERNAL_REVIEW.json")
    _git(repo, "commit", "-m", "review record")
    assert validate_record_commit(repo, "HEAD") == source


def test_record_commit_rejects_any_other_change(tmp_path: Path) -> None:
    repo, _source = _repo(tmp_path)
    (repo / "security" / "EXTERNAL_REVIEW.json").write_text('{"status":"approved"}\n', encoding="utf-8")
    (repo / "source.py").write_text("SOURCE = False\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "mixed record")
    with pytest.raises(ValueError, match="must change only"):
        validate_record_commit(repo, "HEAD")
