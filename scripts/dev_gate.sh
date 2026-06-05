#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

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
export PYTHON="${PYTHON_BIN}"

scripts/public_validation_gate.sh
scripts/strict_schema_gate.sh
scripts/security_regression_gate.sh
"${PYTHON_BIN}" scripts/validate_public_truth.py
"${PYTHON_BIN}" -m pytest -q -p no:cacheprovider
