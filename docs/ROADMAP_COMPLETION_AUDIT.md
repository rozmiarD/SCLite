# SCLite Roadmap Completion Audit

Date: 2026-06-14
Branch: `sclite-roadmap-completion`

This is a repo-local completion audit for the post-1.0 SCLite hardening
roadmap. It is not a Signposter artifact and does not mutate GitHub issues or
open a pull request.

## Scope Reviewed

The roadmap was consolidated from 48 open DAG items in the writable GitHub
fork. The items were intentionally delivered as larger engineering blocks
instead of one issue-sized change per task:

- verifier status contracts and public API/docs alignment;
- strict lifecycle and approval/ticket fail-safe semantics;
- receipt/evidence compatibility and public-safe review output;
- Kernel Guard, replay non-claims, host freshness handoff, and filesystem
  boundaries;
- schema compatibility, package/release gates, downstream GovEngine smoke, and
  final validation.

## Delivered Blocks

### Verifier Status Contract

- `validate-chain`, strict lifecycle, Kernel Guard, and secure-bundle result
  surfaces now expose explicit layer statuses.
- `verification_result.v1` remains aligned with `guarded-strict` non-claims.
- Public docs and public-truth validation cover the status vocabulary.

### Lifecycle Safety

- Strict lifecycle verification rejects policy `deny`, owner-approval-required
  chains without consumable approval, terminal ticket approvals, and missing or
  unknown approval states.
- `verify_lifecycle_manifest()` is exported as the public fail-safe Python API.
- Public API freeze tests require docs updates for any additive top-level
  export.

### Receipt And Evidence

- Structured evidence claim booleans are authoritative.
- Legacy text markers remain a conservative v0.2 compatibility fallback.
- Negative tests cover network/completed/live-execution overclaims, descriptor
  drift, and replay live-execution requirements.
- Review-bundle materialization is covered against leaking raw private fixture
  values into public JSON or Markdown output.

### Kernel Guard And Replay Boundary

- Guarded and secure verifier paths continue to report replay as
  `not_checked`.
- `verify-secure-bundle` now requires manifest and Kernel Guard sidecar paths
  to remain under the verification root after symlink resolution.
- Existing Kernel Guard golden-vector and stale-guard tests remain intact.
- Docs define host freshness handoff inputs such as `root_chain_digest`,
  `guard_root_tag`, `chain_id`, `key_id`, ticket/run id, observed time, and
  host admission context.

### Compatibility And Release Readiness

- `docs/SCHEMA_COMPATIBILITY.md` documents current, legacy-current, planned,
  and unsupported schema combinations.
- Unknown fields are documented as metadata unless named and validated by
  SCLite code.
- Artifact IDs are documented as labels unless descriptor/digest-bound.
- GovEngine compatibility remains a consumer smoke and one-way dependency.
- `scripts/package_smoke.sh` builds wheel/sdist in temporary output, runs
  `twine check`, installs the wheel into a clean venv, runs `pip check`, and
  confirms `sclite-core` imports as `sclite`.
- `scripts/security_regression_gate.sh` now includes high-signal lifecycle,
  evidence, public-output, guard, replay-boundary, and path-boundary
  regressions.

## Validation Evidence

Final local checks on this branch passed:

```bash
PYTHON=/tmp/sclite-roadmap-venv/bin/python scripts/dev_gate.sh
/tmp/sclite-roadmap-venv/bin/python -m ruff check .
PYTHON=/tmp/sclite-roadmap-venv/bin/python scripts/package_smoke.sh
```

`scripts/dev_gate.sh` expands to:

- public validation gate;
- strict schema gate;
- security regression gate;
- public truth validator;
- full `pytest -q -p no:cacheprovider`.

Observed successful endpoints:

- `public_truth_ok:sclite-core==1.0.1:import=sclite:runtime_deps=0`
- full pytest completed at 100%;
- `ruff`: `All checks passed!`
- package smoke ended with `sclite_package_smoke_ok:1.0.1`.

## Remaining Risks Outside SCLite Core

- Runtime authorization, admission policy, execution control, and legal
  approval remain host-owned.
- Replay freshness requires host state and atomic check-and-set behavior.
- HMAC key lifecycle, rotation, compromise response, and storage remain
  host-owned.
- Public identity, PKI, non-repudiation, and public signed export remain
  unimplemented.
- Raw evidence retention and private operational logs remain outside SCLite's
  public-safe review bundle.
- Future receipt/evidence vNext work should retire text-marker fallback only
  after explicit schema migration.

## Next Direction

No current-roadmap implementation task remains necessary inside SCLite core.
Future work should be a separate roadmap only if it targets an explicit vNext
schema line, public signature profile, or host-owned downstream integration
outside this package.
