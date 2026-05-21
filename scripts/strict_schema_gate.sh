#!/usr/bin/env bash
set -euo pipefail

python -m sclite.cli validate-artifact --strict-jsonschema --schema intent_contract.v0.2 examples/govengine-integration/01_intent_contract.json
python -m sclite.cli validate-artifact --strict-jsonschema --schema policy_decision.v0.2 examples/govengine-integration/02_policy_decision.json
python -m sclite.cli validate-artifact --strict-jsonschema --schema execution_contract.v0.2 examples/govengine-integration/03_execution_contract.json
python -m sclite.cli validate-artifact --strict-jsonschema --schema execution_ticket.v0.2 sclite/examples/contract-lifecycle-v0.2/execution_ticket.json
python -m sclite.cli validate-artifact --strict-jsonschema --schema execution_ticket.v0.3 examples/govengine-integration/04_execution_ticket.json
python -m sclite.cli validate-artifact --strict-jsonschema --schema execution_receipt.v0.2 examples/govengine-integration/05_execution_receipt.json
python -m sclite.cli validate-artifact --strict-jsonschema --schema evidence_contract.v0.2 examples/govengine-integration/06_evidence_contract.json
python -m sclite.cli validate-artifact --strict-jsonschema --schema artifact_chain_manifest.v0.2 examples/govengine-integration/artifact_chain_manifest.json
python -m sclite.cli validate-artifact --strict-jsonschema --schema review_record.v0.1 examples/govengine-integration/verification_receipt.json
python - <<'PY'
import json
from pathlib import Path
from sclite.scope_fidelity import validate_lifecycle_scope_fidelity_report
record = json.loads(Path('examples/govengine-integration/verification_receipt.json').read_text(encoding='utf-8'))
validate_lifecycle_scope_fidelity_report(record['scope_fidelity_report'], strict_jsonschema=True)
PY
python -m sclite.cli review examples/govengine-integration --strict-jsonschema --format json --fail-on review >/dev/null
python -m sclite.cli review examples/local-admin-change --strict-jsonschema --format json --fail-on review >/dev/null
python -m sclite.cli review-lifecycle sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json --strict-jsonschema --format json >/dev/null
python -m sclite.cli validate-artifact --strict-jsonschema --schema trust_profile_ref.v0.1 examples/govengine-integration/trust_profile_ref.json
python -m sclite.cli validate-artifact --strict-jsonschema --schema carrier_profile_ref.v0.1 examples/govengine-integration/carrier_profile_ref.json
python -m sclite.cli validate-trust-profile examples/govengine-integration/trust_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json --strict-jsonschema
python -m sclite.cli validate-carrier-profile examples/govengine-integration/carrier_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json --strict-jsonschema
