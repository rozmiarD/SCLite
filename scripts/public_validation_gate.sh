#!/usr/bin/env bash
set -euo pipefail

python -m sclite.cli validate examples/security-contract-proof
python -m sclite.cli validate-chain sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json
python -m sclite.cli verify-lifecycle sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json
python -m sclite.cli validate-ticket sclite/examples/scoped-ticket-v0.3/execution_ticket.json --contract sclite/examples/scoped-ticket-v0.3/execution_contract.json
python -m sclite.cli explain-ticket sclite/examples/scoped-ticket-v0.3/execution_ticket.json >/dev/null
python -m sclite.cli verify-ticket-use sclite/examples/scoped-ticket-v0.3/execution_ticket.json --contract sclite/examples/scoped-ticket-v0.3/execution_contract.json --receipt sclite/examples/scoped-ticket-v0.3/execution_receipt.json --evidence-contract sclite/examples/scoped-ticket-v0.3/evidence_contract.json
python -m sclite.cli validate-trust-profile examples/govengine-integration/trust_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json
python -m sclite.cli validate-carrier-profile examples/govengine-integration/carrier_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json
python -m sclite.cli review-lifecycle sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json --format json >/dev/null
python -m sclite.cli review examples/review-bundle --format json >/dev/null
python -m sclite.cli review examples/govengine-integration --format json --fail-on review >/dev/null
python -m sclite.cli review examples/local-admin-change --format json --fail-on review >/dev/null
python -m sclite.cli review examples/bad-review-bundle-cross-host --format json --fail-on none >/dev/null
if python -m sclite.cli review examples/bad-review-bundle-cross-host --format json --fail-on review >/dev/null; then
  echo 'bad review bundle unexpectedly passed --fail-on review' >&2
  exit 1
fi
python -m sclite.cli export-review-bundle examples/govengine-integration --format markdown >/dev/null
python -m sclite.cli validate-artifact --schema prepared_execution_spec.v0.1 examples/prepared-execution-spec/prepared_execution_spec.json
python -m sclite.cli validate-artifact --schema redacted_prepared_execution_spec.v0.1 examples/security-contract-proof/prepared_execution_spec.redacted.json
python -m sclite.cli validate-artifact --schema scope_fidelity_report.v0.1 examples/scope-fidelity-report/scope_fidelity_report.json
python -m sclite.cli validate-artifact --schema review_record.v0.1 examples/govengine-integration/verification_receipt.json
python -m sclite.cli validate-artifact --schema review_record.v0.1 examples/local-admin-change/verification_receipt.json
python -m sclite.cli validate-artifact --schema redaction_policy.v0.1 examples/redaction-policy/redaction_policy.json
python -m sclite.cli validate-artifact --schema redaction_receipt.v0.1 examples/redaction-receipt/redaction_receipt.json
python -m sclite.cli validate-artifact --schema public_validation_surface_index.v0.1 examples/public-validation-surface-index/public_validation_surface_index.json
python -m sclite.cli validate-artifact --schema public_snapshot_manifest.v0.1 examples/public-snapshot-manifest/public_snapshot_manifest.json
python -m sclite.cli hash-artifact --schema approved_execution_spec.v0.1 examples/security-contract-proof/approved_execution_spec.json >/dev/null
python -m sclite.cli scope-fidelity --approved-spec examples/security-contract-proof/approved_execution_spec.json --fail-on review >/dev/null
python -m sclite.cli validation-receipt examples/security-contract-proof >/dev/null
