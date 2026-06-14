# Publication Checklist

This repository is intended to be public-safe, but publication still requires an explicit human decision.

## Identity guard

For maintainer releases from the operator-controlled publish tree, verify the effective repo-local Git identity:

```bash
git config --get user.name
git config --get user.email
```

Required maintainer value for this publish tree:

```text
0x505badc0de <32790662+rozmiarD@users.noreply.github.com>
```

External contributors should use their own GitHub-associated identity; this guardrail is not a contributor identity requirement.

History transparency guardrail: never rewrite already-published history to fix authorship, contribution graphs, cleanup, or cosmetics. No force-push, date rewrite, or tag rewrite for published public history; use corrective commits instead.

## Required local checks

Run from the repository root:

```bash
scripts/dev_gate.sh
```

This expands to public validation, strict schema validation, guarded-strict
security regression tests, public-truth validation, and full pytest. `make
validate` delegates to the same command.

Equivalent expanded commands:

```bash
scripts/public_validation_gate.sh
scripts/strict_schema_gate.sh
scripts/security_regression_gate.sh
python scripts/validate_public_truth.py
python -m pytest -q -p no:cacheprovider
```

For release readiness, also run the opt-in package smoke:

```bash
scripts/package_smoke.sh
```

It builds wheel/sdist artifacts in a temporary directory, runs `twine check`,
installs the generated wheel into a clean virtual environment, runs
`pip check`, and confirms the PyPI distribution name `sclite-core` imports as
the Python package `sclite`.

Before a release-candidate or stable release, confirm the security model and
profile freeze docs remain aligned:

- `SECURITY_MODEL.md`
- `docs/SECURITY_PROFILES.md`
- `SPEC.md`
- README security posture section
- `tests/golden/kernel_guard_hmac_v1/`
- `schemas/verification_result.v1.schema.json`

The public-truth validator must reject removal of the Kernel Guard non-claims,
replay boundary, and transcript/canonicalization freeze language.
The Kernel Guard golden-vector test must reject unversioned changes to
`kernel_guard_hmac_v1` canonicalization, transcript fields, entry tags, or
root tag.
The security regression gate must pass and must remain synthetic-key-only.
`verification_result.v1` must keep replay as host-owned state and
public-identity/runtime-enforcement as explicit non-claims.

For the `1.0.1` stable release, current documentation and validation must
state that the latest published PyPI release is `sclite-core==1.0.1`.

The current release-gate command expansion is defined by
`scripts/public_validation_gate.sh`. The inventory below includes its current
lifecycle/review checks. The retired proof-trace fixture and its CLI commands
must not reappear as installed/current surfaces:

```bash
python -m sclite.cli validate-chain sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json
python -m sclite.cli verify-lifecycle sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json
python -m sclite.cli validate-ticket sclite/examples/scoped-ticket-v0.3/execution_ticket.json --contract sclite/examples/scoped-ticket-v0.3/execution_contract.json
python -m sclite.cli verify-ticket-use sclite/examples/scoped-ticket-v0.3/execution_ticket.json --contract sclite/examples/scoped-ticket-v0.3/execution_contract.json --receipt sclite/examples/scoped-ticket-v0.3/execution_receipt.json --evidence-contract sclite/examples/scoped-ticket-v0.3/evidence_contract.json
python -m sclite.cli review-lifecycle sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json --format json
python -m sclite.cli review examples/review-bundle --format json
python -m sclite.cli review examples/govengine-integration --format json --fail-on review
python -m sclite.cli review examples/local-admin-change --format json --fail-on review
python -m sclite.cli review examples/bad-review-bundle-cross-host --format json --fail-on none
python -m sclite.cli validate-trust-profile examples/govengine-integration/trust_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json
python -m sclite.cli validate-carrier-profile examples/govengine-integration/carrier_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json
python -m sclite.cli export-review-bundle examples/govengine-integration --format markdown
python -m sclite.cli validate-artifact --schema scope_fidelity_report.v0.1 examples/scope-fidelity-report/scope_fidelity_report.json
python -m sclite.cli hash-artifact --schema execution_contract.v0.2 examples/review-bundle/03_execution_contract.json
python -m sclite.cli validate-artifact --schema redaction_policy.v0.1 examples/redaction-policy/redaction_policy.json
python -m sclite.cli validate-artifact --schema redaction_receipt.v0.1 examples/redaction-receipt/redaction_receipt.json
python -m sclite.cli validate-artifact --schema public_validation_surface_index.v0.1 examples/public-validation-surface-index/public_validation_surface_index.json
python -m sclite.cli validate-artifact --schema public_snapshot_manifest.v0.1 examples/public-snapshot-manifest/public_snapshot_manifest.json
python -m sclite.cli scope-fidelity --target https://example.com/login --normalized-arg https://example.com/login --fail-on review
python -m pytest -q
```

Expected state:

- current lifecycle/review fixtures validate and retired proof-trace product
  files/commands remain absent;
- lifecycle chain and semantic lifecycle verification pass;
- scoped-ticket validation and ticket-use/evidence-bound checks pass;
- lifecycle review records, review bundles, GovEngine integration fixture, and negative drift fixture validate as expected;
- local-admin-change review bundle validates as a second public-safe non-security fixture;
- public truth validator passes for the current published stable package truth;
- Scope Fidelity fixture validates;
- generated Scope Fidelity report exits cleanly;
- pytest passes.

## Residue review

Before public push/package publication, review for:

- credentials or tokens;
- cookies or session material;
- private paths;
- raw stdout/stderr from real runs;
- internal hostnames;
- generated caches;
- virtual environments;
- package build artifacts;
- private runtime logs;
- Ravenclaw workspace-only files;
- live target evidence.

This repository should contain only synthetic examples and public-safe docs/code.

## Claim review

Confirm docs do not claim that SCLite/SCL v0.2/v0.3:

- is a standard;
- is a protocol;
- executes tools;
- proves legal authorization;
- proves live vulnerabilities;
- is tamper-proof;
- includes identity signatures or PKI trust;
- includes OpenClaw/MCP/A2A adapters;
- replaces a runtime policy engine or executor.

## Package build checks

Before any TestPyPI or PyPI upload, run from a clean tree:

```bash
scripts/package_smoke.sh
```

This is a local release-readiness gate only. It does not upload, tag, or
authorize publication.

Do not commit `build/`, `dist/`, `*.egg-info`, caches, or virtual environments.

## Publication decision

Before any public push:

- confirm repository name/owner;
- confirm remote URL;
- confirm branch to push;
- confirm local git status is clean;
- run the checks above on the exact tree to be pushed;
- confirm the PyPI distribution name is `sclite-core` and the Python import package remains `sclite`;
- decide whether the validated current tree is authorized for release;
- get explicit operator approval for any tag, TestPyPI upload, or PyPI upload.

Validation receipts do not authorize publication. They only record checks.
