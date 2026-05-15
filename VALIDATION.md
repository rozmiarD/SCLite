# SCLite Validation

SCLite validation is local and public-safe. It does not run live targets.

The roadmap in `ROADMAP.md` preserves this boundary: scoped-ticket, receipt-bounded-evidence, trust-profile, carrier-profile, and review-bundle checks remain artifact validation/review surfaces unless explicitly implemented in an external runtime.

## Fast local gate

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
```

## Publication validation gate

Run the full public-safe checklist from the repository root:

```bash
scripts/public_validation_gate.sh
scripts/strict_schema_gate.sh
python -m pytest -q
```

The scripts expand to the public-safe fixture, lifecycle, ticket, profile, review-bundle, negative-bundle, and strict-schema checks. The equivalent command set starts with:

```bash
python -m sclite.cli validate examples/security-contract-proof
python -m sclite.cli validate-chain sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json
python -m sclite.cli verify-lifecycle sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json
python -m sclite.cli validate-ticket sclite/examples/scoped-ticket-v0.3/execution_ticket.json --contract sclite/examples/scoped-ticket-v0.3/execution_contract.json
python -m sclite.cli explain-ticket sclite/examples/scoped-ticket-v0.3/execution_ticket.json
python -m sclite.cli verify-ticket-use sclite/examples/scoped-ticket-v0.3/execution_ticket.json --contract sclite/examples/scoped-ticket-v0.3/execution_contract.json --receipt sclite/examples/scoped-ticket-v0.3/execution_receipt.json --evidence-contract sclite/examples/scoped-ticket-v0.3/evidence_contract.json
python -m sclite.cli review-lifecycle sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json --format json
python -m sclite.cli review examples/review-bundle --format json
python -m sclite.cli review examples/govengine-integration --format json --fail-on review
python -m sclite.cli review examples/bad-review-bundle-cross-host --format json --fail-on none
python -m sclite.cli validate-trust-profile examples/govengine-integration/trust_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json
python -m sclite.cli validate-carrier-profile examples/govengine-integration/carrier_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json
python -m sclite.cli export-review-bundle examples/govengine-integration --format markdown
python -m sclite.cli validate-artifact --schema prepared_execution_spec.v0.1 examples/prepared-execution-spec/prepared_execution_spec.json
python -m sclite.cli validate-artifact --strict-jsonschema --schema prepared_execution_spec.v0.1 examples/prepared-execution-spec/prepared_execution_spec.json
python -m sclite.cli validate-artifact --schema redacted_prepared_execution_spec.v0.1 examples/security-contract-proof/prepared_execution_spec.redacted.json
python -m sclite.cli validate-artifact --schema scope_fidelity_report.v0.1 examples/scope-fidelity-report/scope_fidelity_report.json
python -m sclite.cli hash-artifact --schema approved_execution_spec.v0.1 examples/security-contract-proof/approved_execution_spec.json
python -m sclite.cli validate-artifact --schema redaction_policy.v0.1 examples/redaction-policy/redaction_policy.json
python -m sclite.cli validate-artifact --schema redaction_receipt.v0.1 examples/redaction-receipt/redaction_receipt.json
python -m sclite.cli validate-artifact --schema public_validation_surface_index.v0.1 examples/public-validation-surface-index/public_validation_surface_index.json
python -m sclite.cli validate-artifact --schema public_snapshot_manifest.v0.1 examples/public-snapshot-manifest/public_snapshot_manifest.json
python -m sclite.cli scope-fidelity --approved-spec examples/security-contract-proof/approved_execution_spec.json --fail-on review
python -m sclite.cli validation-receipt examples/security-contract-proof
python -m pytest -q
```

Expected result:

- fixture validation passes;
- v0.2 lifecycle chain validation and semantic lifecycle verification pass;
- v0.3 scoped-ticket schema, binding, explanation, and static ticket-use checks pass;
- lifecycle review records and lifecycle-aware Scope Fidelity checks are generated conservatively;
- canonical review bundles validate and export to Markdown;
- GovEngine integration fixture passes with `--fail-on review`;
- the intentional cross-host negative fixture fails when `--fail-on review` is enforced;
- artifact schema validation passes in default dependency-free mode and optional strict Draft 2020-12 mode;
- hash and Scope Fidelity commands complete;
- validation receipt reports `status: passed`;
- pytest passes.

## Package build gate

Before any future PyPI/TestPyPI release candidate:

```bash
python -m pip install build twine
python -m build
python -m twine check dist/*
```

Then test install from the generated wheel in a clean environment and confirm the distribution name `sclite-core` still imports as `sclite`.

## Non-claims

Passing validation does not prove:

- legal authorization;
- live vulnerability evidence;
- execution safety;
- production deployment readiness;
- adapter/protocol correctness.
