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
  tests/test_integrity_chain.py::test_v02_lifecycle_rejects_policy_deny_with_executable_chain \
  tests/test_integrity_chain.py::test_v02_lifecycle_rejects_owner_approval_required_without_consumable_ticket \
  tests/test_integrity_chain.py::test_v02_lifecycle_rejects_terminal_ticket_approval_statuses \
  tests/test_integrity_chain.py::test_v02_lifecycle_rejects_missing_ticket_approval_status \
  tests/test_ticket_use_negative.py::test_ticket_use_rejects_structured_network_overclaim_without_text_marker \
  tests/test_ticket_use_negative.py::test_ticket_use_keeps_legacy_text_marker_compatibility \
  tests/test_ticket_use_negative.py::test_ticket_use_rejects_evidence_replay_live_execution_requirement \
  tests/test_review_bundles.py::test_materialized_review_output_excludes_raw_private_fixture_values \
  -p no:cacheprovider
