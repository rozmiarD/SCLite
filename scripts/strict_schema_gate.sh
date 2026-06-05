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

"${PYTHON_BIN}" -m sclite.cli validate-artifact --strict-jsonschema --schema intent_contract.v0.2 examples/govengine-integration/01_intent_contract.json
"${PYTHON_BIN}" -m sclite.cli validate-artifact --strict-jsonschema --schema policy_decision.v0.2 examples/govengine-integration/02_policy_decision.json
"${PYTHON_BIN}" -m sclite.cli validate-artifact --strict-jsonschema --schema execution_contract.v0.2 examples/govengine-integration/03_execution_contract.json
"${PYTHON_BIN}" -m sclite.cli validate-artifact --strict-jsonschema --schema execution_ticket.v0.2 sclite/examples/contract-lifecycle-v0.2/execution_ticket.json
"${PYTHON_BIN}" -m sclite.cli validate-artifact --strict-jsonschema --schema execution_ticket.v0.3 examples/govengine-integration/04_execution_ticket.json
"${PYTHON_BIN}" -m sclite.cli validate-artifact --strict-jsonschema --schema execution_receipt.v0.2 examples/govengine-integration/05_execution_receipt.json
"${PYTHON_BIN}" -m sclite.cli validate-artifact --strict-jsonschema --schema evidence_contract.v0.2 examples/govengine-integration/06_evidence_contract.json
"${PYTHON_BIN}" -m sclite.cli validate-artifact --strict-jsonschema --schema artifact_chain_manifest.v0.2 examples/govengine-integration/artifact_chain_manifest.json
"${PYTHON_BIN}" -m sclite.cli validate-artifact --strict-jsonschema --schema review_record.v0.1 examples/govengine-integration/verification_receipt.json
"${PYTHON_BIN}" - <<'PY'
from sclite.artifacts import validate_artifact
sample = {
    'artifact_type': 'verification_result',
    'schema_version': 'v1',
    'schema_ref': 'schemas/verification_result.v1.schema.json',
    'profile': 'guarded-strict',
    'security_posture': 'guarded_domain_auth',
    'status': 'pass',
    'artifact_chain': 'pass',
    'strict_lifecycle': 'pass',
    'kernel_guard': 'pass',
    'replay': 'not_checked',
    'public_identity': 'not_claimed',
    'runtime_enforcement': 'not_claimed',
    'entry_count': 6,
    'checked_entries': ['intent_contract'],
    'root_chain_digest': 'a' * 64,
    'guard_profile': 'kernel_guard_hmac_v1',
    'guard_root_tag': 'b' * 64,
    'key_id': 'test-key',
}
validate_artifact(sample, 'verification_result.v1', strict_jsonschema=True)
PY
"${PYTHON_BIN}" - <<'PY'
import json
from pathlib import Path
from sclite.scope_fidelity import validate_lifecycle_scope_fidelity_report
record = json.loads(Path('examples/govengine-integration/verification_receipt.json').read_text(encoding='utf-8'))
validate_lifecycle_scope_fidelity_report(record['scope_fidelity_report'], strict_jsonschema=True)
PY
"${PYTHON_BIN}" -m sclite.cli review examples/govengine-integration --strict-jsonschema --format json --fail-on review >/dev/null
"${PYTHON_BIN}" -m sclite.cli review examples/local-admin-change --strict-jsonschema --format json --fail-on review >/dev/null
"${PYTHON_BIN}" -m sclite.cli review-lifecycle sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json --strict-jsonschema --format json >/dev/null
"${PYTHON_BIN}" -m sclite.cli validate-artifact --strict-jsonschema --schema trust_profile_ref.v0.1 examples/govengine-integration/trust_profile_ref.json
"${PYTHON_BIN}" -m sclite.cli validate-artifact --strict-jsonschema --schema carrier_profile_ref.v0.1 examples/govengine-integration/carrier_profile_ref.json
"${PYTHON_BIN}" -m sclite.cli validate-trust-profile examples/govengine-integration/trust_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json --strict-jsonschema
"${PYTHON_BIN}" -m sclite.cli validate-carrier-profile examples/govengine-integration/carrier_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json --strict-jsonschema
