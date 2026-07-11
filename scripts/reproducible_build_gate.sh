#!/usr/bin/env bash
set -euo pipefail

left="$(mktemp -d)"
right="$(mktemp -d)"
export SOURCE_DATE_EPOCH=1704067200
python_bin="${PYTHON:-python3}"
"$python_bin" -m build --wheel --outdir "$left" >/dev/null
"$python_bin" -m build --wheel --outdir "$right" >/dev/null
left_hash="$(sha256sum "$left"/*.whl | cut -d' ' -f1)"
right_hash="$(sha256sum "$right"/*.whl | cut -d' ' -f1)"
test "$left_hash" = "$right_hash"
echo "reproducible_wheel_ok:$left_hash"
