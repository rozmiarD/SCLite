#!/usr/bin/env bash
set -euo pipefail

left="$(mktemp -d)"
right="$(mktemp -d)"
export SOURCE_DATE_EPOCH=1704067200
python_bin="${PYTHON:-python3}"
"$python_bin" -m build --wheel --sdist --outdir "$left" >/dev/null
"$python_bin" -m build --wheel --sdist --outdir "$right" >/dev/null
scripts/normalize_sdist.sh "$left"/*.tar.gz
scripts/normalize_sdist.sh "$right"/*.tar.gz
for suffix in whl tar.gz; do
  left_hash="$(sha256sum "$left"/*.$suffix | cut -d' ' -f1)"
  right_hash="$(sha256sum "$right"/*.$suffix | cut -d' ' -f1)"
  test "$left_hash" = "$right_hash"
  echo "reproducible_${suffix//./_}_ok:$left_hash"
done
