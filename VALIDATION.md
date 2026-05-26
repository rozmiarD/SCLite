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
python scripts/validate_public_truth.py
python -m pytest -q
```

The dependency-free validator is intentionally a subset validator. It exists so SCLite can keep zero runtime dependencies and still validate the repository's simple schema shapes in offline/minimal environments. It is not a full JSON Schema Draft 2020-12 implementation.

| JSON Schema keyword | Dependency-free subset | Strict `jsonschema` mode |
| --- | --- | --- |
| `const` | supported | supported |
| `enum` | supported | supported |
| `type` | supported, including simple type arrays | supported |
| `required` | supported | supported |
| `properties` | supported recursively | supported |
| `additionalProperties: false` | supported | supported |
| `items` with one schema | supported recursively | supported |
| `minLength` | supported | supported |
| `minimum` | supported | supported |
| `pattern`, `format`, `maxLength`, `maximum`, `oneOf`, `anyOf`, `allOf`, `not`, `if/then/else`, `dependentRequired`, `uniqueItems` | not implemented by the subset validator | supported according to `jsonschema` behavior |

For CI and release validation, run both:

```bash
scripts/public_validation_gate.sh
scripts/strict_schema_gate.sh
```

If strict mode and subset mode disagree, treat strict mode as authoritative for release readiness and either simplify the schema or add explicit implementation/tests for the missing subset keyword.

The scripts expand to the current lifecycle, ticket, profile, review-bundle,
negative-bundle, and strict-schema checks. The superseded proof-trace fixture
and its validation commands are retired; they are not part of this release
gate or the installed package. The equivalent current
command set starts with:

```bash
python -m sclite.cli validate-chain sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json
python -m sclite.cli verify-lifecycle sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json
python -m sclite.cli validate-ticket sclite/examples/scoped-ticket-v0.3/execution_ticket.json --contract sclite/examples/scoped-ticket-v0.3/execution_contract.json
python -m sclite.cli explain-ticket sclite/examples/scoped-ticket-v0.3/execution_ticket.json
python -m sclite.cli verify-ticket-use sclite/examples/scoped-ticket-v0.3/execution_ticket.json --contract sclite/examples/scoped-ticket-v0.3/execution_contract.json --receipt sclite/examples/scoped-ticket-v0.3/execution_receipt.json --evidence-contract sclite/examples/scoped-ticket-v0.3/evidence_contract.json
python -m sclite.cli review-lifecycle sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json --format json
python -m sclite.cli review examples/review-bundle --format json
python -m sclite.cli review examples/govengine-integration --format json --fail-on review
python -m sclite.cli review examples/local-admin-change --format json --fail-on review
python -m sclite.cli review examples/bad-review-bundle-cross-host --format json --fail-on none
python -m sclite.cli validate-trust-profile examples/govengine-integration/trust_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json
python -m sclite.cli validate-carrier-profile examples/govengine-integration/carrier_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json
python -m sclite.cli export-review-bundle examples/govengine-integration --format markdown
python -m sclite.cli validate-artifact --schema redaction_policy.v0.1 examples/redaction-policy/redaction_policy.json
python -m sclite.cli validate-artifact --schema redaction_receipt.v0.1 examples/redaction-receipt/redaction_receipt.json
python -m sclite.cli validate-artifact --schema public_validation_surface_index.v0.1 examples/public-validation-surface-index/public_validation_surface_index.json
python -m sclite.cli validate-artifact --schema public_snapshot_manifest.v0.1 examples/public-snapshot-manifest/public_snapshot_manifest.json
python -m pytest -q
```

`verify-lifecycle` is stricter than generic chain validation. It requires the
canonical v0.2 lifecycle role sequence exactly, with no extra roles, duplicate
roles, or changed order. `validate-chain` remains available for generic
hash-chain verification; pass `--strict-lifecycle` when that command should
also enforce lifecycle role strictness.

`verify-guarded-chain` is optional. It verifies a `kernel_guard_hmac_v1`
sidecar when a GovEngine/KERNEL-domain HMAC secret is available through
`--guard-key-env` (default: `SCLITE_KERNEL_GUARD_KEY`). This command does not
check replay freshness; GovEngine or another runtime must keep the replay
store for `root_tag`, `chain_id`, ticket/run id, and `key_id`.

For runtime-consumable guarded bundles, prefer the fail-closed profile:

```bash
SCLITE_KERNEL_GUARD_KEY='local-test-secret' \
python -m sclite.cli verify-secure-bundle examples/govengine-integration \
  --guard kernel_guard_manifest.json
```

`verify-secure-bundle` is `guarded-strict`: artifact-chain verification,
strict lifecycle, `kernel_guard_hmac_v1`, manifest metadata binding, and
fail-on-missing-guard. `validate-chain`, `verify-lifecycle`,
`review-lifecycle`, and `review` also expose `--require-guard` /
`--fail-on-unguarded` for callers that intentionally want guard preflight on
those older commands.

## Review-bundle compatibility

The stable `0.5` review-bundle shape remains the downstream compatibility
boundary for GovEngine and Ravenclaw on the `0.8` beta candidate. Consumers may
rely on the canonical `review_bundle` directory shape, the
`review_record.v0.1` output contract, the `sclite-review-bundle-v0.1` review
profile, and `review_bundle:<verdict>:<artifact_count>:<root_chain_digest>`
summary output. They must not assume a security fixture story, private fixture
paths, runtime execution, trust authority, or adapter behavior from the bundle.

`tests/test_review_bundles.py` keeps the public-safe GovEngine integration and
local-admin-change fixture families aligned at that contract level while their
domain narratives remain different.

Expected result:

- current lifecycle/review fixture validation passes;
- v0.2 lifecycle chain validation and strict semantic lifecycle verification
  pass;
- v0.3 scoped-ticket schema, binding, explanation, and static ticket-use checks pass;
- lifecycle review records and lifecycle-aware Scope Fidelity checks are generated conservatively;
- canonical review bundles validate and export to Markdown;
- GovEngine integration fixture passes with `--fail-on review`;
- local-admin-change fixture passes with `--fail-on review` and demonstrates the same lifecycle outside the security-domain fixture path;
- the intentional cross-host negative fixture fails when `--fail-on review` is enforced;
- public truth validation distinguishes the `0.8.0b2` source candidate from
  the latest published `0.8.0a0` package line;
- optional `kernel_guard_hmac_v1` sidecar verification detects guard, metadata,
  sequence, previous-tag, and root-tag drift when a guard key is supplied;
- secure-bundle verification fails closed on missing guard, loose lifecycle,
  metadata spoofing, and full-chain forgery attempts using an old guard;
- artifact schema validation passes in default dependency-free mode and optional strict Draft 2020-12 mode;
- hash and Scope Fidelity commands complete;
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
