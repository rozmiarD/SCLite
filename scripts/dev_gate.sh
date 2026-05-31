#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

scripts/public_validation_gate.sh
scripts/strict_schema_gate.sh
scripts/security_regression_gate.sh
python scripts/validate_public_truth.py
python -m pytest -q -p no:cacheprovider
