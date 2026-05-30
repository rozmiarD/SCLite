#!/usr/bin/env bash
set -euo pipefail

export PYTEST_DISABLE_PLUGIN_AUTOLOAD="${PYTEST_DISABLE_PLUGIN_AUTOLOAD:-1}"

python -m pytest -q \
  tests/test_kernel_guard.py \
  tests/test_secure_bundle.py \
  tests/test_integrity_chain.py::test_v02_lifecycle_strict_rejects_extra_role \
  tests/test_integrity_chain.py::test_v02_lifecycle_strict_rejects_duplicate_role_without_overwrite \
  -p no:cacheprovider
