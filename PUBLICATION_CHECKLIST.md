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
Krzysztof Probola <32790662+rozmiarD@users.noreply.github.com>
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

`scripts/build_release_artifacts.sh` builds wheel/sdist artifacts, normalizes
the sdist, runs `twine check`, and runs exact distribution-metadata validation.
After that helper succeeds, `scripts/package_smoke.sh` separately installs the
generated wheel and sdist into clean virtual environments, runs `pip check` for
both, and confirms `sclite-core` imports as `sclite` with the expected version.

The smoke environment installs `.github/release-build-requirements.txt`; it does
not resolve floating build or upload-tool versions. The release workflow uses
separate exact audit and test requirement sets before running `dev_gate.sh`.
Its product SBOM is generated after the exact wheel exists from a clean target
environment containing only that wheel, then validated against the wheel
metadata while emitting the wheel SHA-256 alongside the identity result. The
CycloneDX document is not intrinsically byte-bound and does not replace release
provenance or checksums; this evidence does not replace the dependency audit.

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

## Source-versus-published truth

Source and publication identities are separate durable facts. When the current
source version differs from the latest published package, active release-truth
documents must state both values and must describe publication as pending. The
README source badge and current-source wording must use the source version;
the PyPI badge, PyPI link and exact PyPI install command must use only the
latest published version.

For the current maintenance source, expected truth is:

- current source version and source release label: `2.0.1`;
- source status: unpublished non-prerelease 2.0.1 release source; publication
  pending;
- latest published PyPI package, badge, link and install pin:
  `sclite-core==2.0.0`.

The `2.0.1` source must not be described as published or installable from PyPI
unless publication has completed and every source-versus-published truth check
is updated in the same reviewed change. For each stable release, current
documentation and validation must state the exact latest published PyPI release
tracked by `scripts/validate_public_truth.py`.

The immutable package long description is
[`PYPI_LONG_DESCRIPTION.md`](PYPI_LONG_DESCRIPTION.md), not the mutable
README. Public truth binds its approved SHA-256. The canonical metadata gate
compares its exact source bytes with the built wheel `METADATA` and exact root
sdist `PKG-INFO`, including project identity, version, and Markdown content
type. It tolerates the standard nested setuptools egg-info `PKG-INFO`; it is
not a natural-language classifier, a shell/YAML policy engine, a general
archive sanitizer, or proof of publication, provenance, authorization, or
human approval.

The current release-gate command expansion is defined by
`scripts/public_validation_gate.sh`. The inventory below includes its current
lifecycle/review checks. The retired proof-trace fixture and its CLI commands
must not reappear as installed/current surfaces:

```bash
python -m sclite.kernel_cli validate-chain sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json
python -m sclite.kernel_cli verify-lifecycle sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json
python -m sclite.kernel_cli validate-ticket sclite/examples/scoped-ticket-v0.3/execution_ticket.json --contract sclite/examples/scoped-ticket-v0.3/execution_contract.json
python -m sclite.kernel_cli verify-ticket-use sclite/examples/scoped-ticket-v0.3/execution_ticket.json --contract sclite/examples/scoped-ticket-v0.3/execution_contract.json --receipt sclite/examples/scoped-ticket-v0.3/execution_receipt.json --evidence-contract sclite/examples/scoped-ticket-v0.3/evidence_contract.json
python -m sclite.devtools review-lifecycle sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json --format json
python -m sclite.kernel_cli review examples/review-bundle --format json
python -m sclite.kernel_cli review examples/govengine-integration --format json --fail-on review
python -m sclite.kernel_cli review examples/local-admin-change --format json --fail-on review
python -m sclite.kernel_cli review examples/bad-review-bundle-cross-host --format json --fail-on none
python -m sclite.kernel_cli validate-trust-profile examples/govengine-integration/trust_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json
python -m sclite.kernel_cli validate-carrier-profile examples/govengine-integration/carrier_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json
python -m sclite.kernel_cli export-review-bundle examples/govengine-integration --mode local_review --format markdown
python -m sclite.kernel_cli validate-artifact --schema scope_fidelity_report.v0.1 examples/scope-fidelity-report/scope_fidelity_report.json
python -m sclite.devtools hash-artifact --schema execution_contract.v0.2 examples/review-bundle/03_execution_contract.json
python -m sclite.kernel_cli validate-artifact --schema redaction_policy.v0.2 examples/redaction-policy/redaction_policy.json
python -m sclite.kernel_cli validate-artifact --schema redaction_receipt.v0.2 examples/redaction-receipt/redaction_receipt.json
python -m sclite.kernel_cli validate-artifact --schema public_validation_surface_index.v0.2 examples/public-validation-surface-index/public_validation_surface_index.json
python -m sclite.kernel_cli validate-artifact --schema public_snapshot_manifest.v0.2 examples/public-snapshot-manifest/public_snapshot_manifest.json
python -m sclite.devtools scope-fidelity --target https://example.com/login --normalized-arg https://example.com/login --fail-on review
python -m pytest -q
```

Expected state:

- current lifecycle/review fixtures validate and retired proof-trace product
  files/commands remain absent;
- lifecycle chain and semantic lifecycle verification pass;
- scoped-ticket validation and ticket-use/evidence-bound checks pass;
- lifecycle review records, review bundles, GovEngine integration fixture, and negative drift fixture validate as expected;
- local-admin-change review bundle validates as a second public-safe non-security fixture;
- public truth validator passes for the current-source/latest-published split;
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
- downstream workspace-only files;
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

For stable 2.0, prepare the final source/version commit first and have the
reviewer confirm that commit and reproducible artifacts. Then create one
record-only child commit changing `security/EXTERNAL_REVIEW.json`, and tag that
child. Never mix code, version, workflow, documentation, or fixture changes into
the record commit; the release workflow rejects such a tag.

The stable workflow builds reviewed source commit `A`, then rebuilds tagged
record commit `B`. It requires the wheel and normalized sdist names and bytes to
match exactly, rejects a packaged external-review record, publishes the `B`
build, and attests `B` as the actual build commit. Before creating `B`, confirm
that `review_verdict`, all severity counts and `accepted_findings` agree.
Accepted finding IDs must use `M-...` or `L-...` and match the corresponding
counter; the review date must be a real ISO calendar date.
`report_sha256` is release-owner-attested metadata: CI validates its format but
does not retrieve or independently hash the retained report.

If release tooling fails closed before upload, never move or recreate the
public tag. Correct the tooling on `main`, validate the new pins, and invoke the
Release workflow manually with the existing immutable tag. The recovery path
must revalidate A/B, reproduce identical artifacts and emit its explicit signed
recovery attestation.
If the runner produces different hashes from a locally reviewed build, obtain
new explicit human approval and bind the exact runner hashes in
`security/EXTERNAL_REVIEW_RECOVERY.json` before dispatching again.
