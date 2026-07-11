#!/usr/bin/env bash
set -euo pipefail

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

"${PYTHON_BIN}" -m sclite.kernel_cli validate-chain sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json
"${PYTHON_BIN}" -m sclite.kernel_cli verify-lifecycle sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json
"${PYTHON_BIN}" -m sclite.kernel_cli validate-ticket sclite/examples/scoped-ticket-v0.3/execution_ticket.json --contract sclite/examples/scoped-ticket-v0.3/execution_contract.json
"${PYTHON_BIN}" -m sclite.devtools explain-ticket sclite/examples/scoped-ticket-v0.3/execution_ticket.json >/dev/null
"${PYTHON_BIN}" -m sclite.kernel_cli verify-ticket-use sclite/examples/scoped-ticket-v0.3/execution_ticket.json --contract sclite/examples/scoped-ticket-v0.3/execution_contract.json --receipt sclite/examples/scoped-ticket-v0.3/execution_receipt.json --evidence-contract sclite/examples/scoped-ticket-v0.3/evidence_contract.json
"${PYTHON_BIN}" -m sclite.kernel_cli validate-trust-profile examples/govengine-integration/trust_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json
"${PYTHON_BIN}" -m sclite.kernel_cli validate-carrier-profile examples/govengine-integration/carrier_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json
"${PYTHON_BIN}" -m sclite.devtools review-lifecycle sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json --format json >/dev/null
"${PYTHON_BIN}" -m sclite.kernel_cli review examples/review-bundle --format json >/dev/null
"${PYTHON_BIN}" -m sclite.kernel_cli review examples/govengine-integration --format json --fail-on review >/dev/null
"${PYTHON_BIN}" -m sclite.kernel_cli review examples/local-admin-change --format json --fail-on review >/dev/null
"${PYTHON_BIN}" -m sclite.kernel_cli review examples/bad-review-bundle-cross-host --format json --fail-on none >/dev/null
if "${PYTHON_BIN}" -m sclite.kernel_cli review examples/bad-review-bundle-cross-host --format json --fail-on review >/dev/null; then
  echo 'bad review bundle unexpectedly passed --fail-on review' >&2
  exit 1
fi
"${PYTHON_BIN}" -m sclite.kernel_cli export-review-bundle examples/govengine-integration \
  --mode local_review --format markdown >/dev/null
"${PYTHON_BIN}" -m sclite.kernel_cli validate-artifact --schema review_record.v0.1 examples/govengine-integration/verification_receipt.json
"${PYTHON_BIN}" -m sclite.kernel_cli validate-artifact --schema review_record.v0.1 examples/local-admin-change/verification_receipt.json
"${PYTHON_BIN}" -m sclite.kernel_cli validate-artifact --schema redaction_policy.v0.2 examples/redaction-policy/redaction_policy.json
"${PYTHON_BIN}" -m sclite.kernel_cli validate-artifact --schema redaction_receipt.v0.2 examples/redaction-receipt/redaction_receipt.json
"${PYTHON_BIN}" -m sclite.kernel_cli validate-artifact --schema public_validation_surface_index.v0.2 examples/public-validation-surface-index/public_validation_surface_index.json
"${PYTHON_BIN}" -m sclite.kernel_cli validate-artifact --schema public_snapshot_manifest.v0.2 examples/public-snapshot-manifest/public_snapshot_manifest.json
