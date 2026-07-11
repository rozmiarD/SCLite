#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
repo_root="$(pwd)"
python_candidate="${PYTHON:-python3}"
if [[ "$python_candidate" == */* ]]; then
  python_bin="$(realpath "$python_candidate")"
else
  python_bin="$(command -v "$python_candidate")"
fi
work="$(mktemp -d)"
cleanup() { rm -rf "$work"; }
trap cleanup EXIT

export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1704067200}"
git clone --quiet --no-local "$repo_root" "$work/repo"
cd "$work/repo"
source_commit="$(git rev-parse HEAD)"
mkdir -p "$work/reviewed" "$work/published"

"$python_bin" -m build --outdir "$work/reviewed" >/dev/null
scripts/normalize_sdist.sh "$work"/reviewed/*.tar.gz

"$python_bin" - security/EXTERNAL_REVIEW.json <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
record = json.loads(path.read_text(encoding="utf-8"))
record["status"] = "a_b_repro_gate_record_only_child"
path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
PY
git config user.name "SCLite release gate"
git config user.email "release-gate@example.invalid"
git add security/EXTERNAL_REVIEW.json
git commit --quiet -m "Create record-only A/B gate child"
test "$("$python_bin" scripts/validate_release_record_commit.py --review-commit HEAD)" = "$source_commit"

# Cross a wall-clock tick so equality cannot depend on near-simultaneous builds.
sleep 2
"$python_bin" -m build --outdir "$work/published" >/dev/null
scripts/normalize_sdist.sh "$work"/published/*.tar.gz
"$python_bin" scripts/compare_release_builds.py \
  --reviewed "$work/reviewed" \
  --published "$work/published"
