# SCLite Public Status

SCLite is a lightweight Security Contract Layer lifecycle package.

The current candidate exposes an immutable explicit schema resolver and neutral
trust/carrier v0.2 bindings. RExecOp owns orchestration-specific reaction,
trigger, watchdog and automation contract resources. Copies shipped by SCLite
1.x are deprecated migration shims, not core ownership.

## Current maturity

- Current release version: `1.1.0rc1`.
- Release label: `1.1.0rc1`.
- Status: unpublished verifier-hardening candidate; the published stable line remains `1.0.9`.
- Runtime dependencies: none.
- CLI: available as `sclite` and `scl`.
- CI: GitHub Actions validation exists.
- Latest published PyPI package: `sclite-core==1.0.9` (`1.0.9`).

## Current review path

For new public demos and integrations, the clearest path is:

```text
current lifecycle artifacts -> artifact_chain_manifest -> review bundle -> review_record verification receipt
```

The superseded proof-trace fixtures/builders/CLI have been retired after the controlled Ravenclaw migration and are not part of the installed/current surface. Scoped-ticket checks, `examples/review-bundle/`, `examples/govengine-integration/`, and `examples/local-admin-change/` form the review-lifecycle front door. Schema identifiers such as `review_record.v0.1` describe retained formats, not an older supported product line.

## What is public-safe today

SCLite can be reviewed as a package for:

- JSON schemas for contract lifecycle artifacts;
- synthetic public-safe fixtures;
- deterministic artifact descriptors;
- hash-linked artifact-chain manifests;
- lifecycle verification helpers;
- redaction helpers;
- Scope Fidelity reports;
- validation-surface and snapshot-manifest helpers;
- scoped-ticket validation and explanation helpers;
- first static ticket-use / receipt-bounded-evidence verification helper;
- initial digest-bound trust/carrier profile reference checks, without PKI/trust/adapter ownership;
- initial lifecycle review records and lifecycle-aware Scope Fidelity v0.2;
- canonical review-bundle validation and Markdown export helpers;
- GovEngine integration-readiness fixture, stable import/CLI contract, CLI exit-code docs, and negative drift fixtures;
- local-admin-change review bundle proving the same lifecycle outside the security-domain fixture path;
- public truth validation for version, maturity, package badge/install, dependency-free status, public imports, CLI/docs, and non-authority boundaries;
- CLI-based local validation.

## What is not claimed

SCLite does not claim:

- legal authorization to test targets;
- live vulnerability evidence;
- production execution safety;
- scanner/executor/sandbox behavior;
- signer identity or PKI trust;
- tamper-proof transparency log guarantees;
- protocol adapter readiness.

The roadmap keeps those boundaries explicit: SCLite defines and verifies accountability artifacts, while policy, trust, runtime enforcement, adapter implementation, and raw evidence storage remain outside core.

## Release posture

SCLite is published under the PyPI distribution name `sclite-core` while preserving the Python import package name `sclite`.

SCLite is the first package in the Ravenclaw/GovEngine/SCLite family published to PyPI because it is small, dependency-free, CLI-backed, and already versioned.

Before future releases, run the validation and build gates in `PUBLICATION_CHECKLIST.md` and get explicit operator approval for any tag or upload.

The published `1.0.3` line completes the 2026-06-14 audit roadmap v2 hardening.
The `1.0.4` patch adds canonical deterministic-reaction evidence contracts,
digest-bound reaction chains, and an explicitly untrusted escalation-proposal
shape without adding policy, rule interpretation, adapters, or execution.
The `1.0.5` patch adds the typed-package marker and repository quality gates
for downstream type checking. SCLite remains a local artifact validation and
review package, not a policy authority or executor.
The `1.0.6` patch adds the bounded `trigger_decision.v0.1` truth-layer
artifact used by RExecOp trigger/event decisions without adding trigger
planning, scheduling, policy, or execution ownership to SCLite.
The `1.0.7` patch adds the bounded `watchdog_decision.v0.1` truth-layer
artifact for RExecOp runtime-supervisor decisions without adding worker
supervision, recovery authority, infrastructure monitoring, scheduler logic or
execution ownership to SCLite.
The `1.0.8` patch extends `watchdog_decision.v0.1` with optional bounded
manual-recovery context for GovEngine-admitted recovery/break-glass records
without adding recovery authority or runtime supervision to SCLite.
The `1.0.9` patch adds `automation_chain.v0.1` for bounded multi-step
automation-chain truth artifacts without adding traversal, scheduling, policy,
runtime or domain ownership to SCLite.
The `1.1.0rc1` candidate retains the P0 acceptance corrections and adds one
strict JSON input policy with duplicate-key rejection and finite resource
budgets. It continues to use one
immutable verified snapshot per verification, manifest identity/policy checks,
false/unknown scope handling, receipt-window enforcement, and strict
GovEngine lifecycle handoff. It adds no schema family, runtime, governance,
or domain authority.
