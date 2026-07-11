from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


ALLOWED_RECORD_PATH = "security/EXTERNAL_REVIEW.json"


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def validate_record_commit(repo: Path, review_commit: str) -> str:
    parents = _git(repo, "rev-list", "--parents", "-n", "1", review_commit).split()
    if len(parents) != 2:
        raise ValueError("stable review commit must have exactly one parent")
    source_commit = parents[1]
    changed = _git(repo, "diff", "--name-only", source_commit, review_commit).splitlines()
    if changed != [ALLOWED_RECORD_PATH]:
        raise ValueError("stable review commit must change only security/EXTERNAL_REVIEW.json")
    return source_commit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--review-commit", default="HEAD")
    args = parser.parse_args()
    try:
        print(validate_record_commit(args.repo, args.review_commit))
    except (ValueError, subprocess.CalledProcessError) as exc:
        print(f"release_record_commit_invalid:{exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
