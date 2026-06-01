#!/usr/bin/env bash
set -euo pipefail

export PYTEST_DISABLE_PLUGIN_AUTOLOAD="${PYTEST_DISABLE_PLUGIN_AUTOLOAD:-1}"

if [ -n "${PYTHON:-}" ]; then
  PYTHON_BIN="${PYTHON}"
elif [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  echo "python interpreter not found; set PYTHON=/path/to/python" >&2
  exit 127
fi

"${PYTHON_BIN}" -m pytest -q \
  tests/test_kernel_guard.py \
  tests/test_secure_bundle.py \
  tests/test_integrity_chain.py::test_v02_lifecycle_strict_rejects_extra_role \
  tests/test_integrity_chain.py::test_v02_lifecycle_strict_rejects_duplicate_role_without_overwrite \
  -p no:cacheprovider
