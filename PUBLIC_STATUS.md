# SCLite Public Status

SCLite is a lightweight Security Contract Layer lifecycle package.

## Current maturity

- Current package version: `0.8.0a0`.
- Public release label: `0.8.0-alpha`.
- Status: alpha multi-runtime proof/review substrate.
- Runtime dependencies: none.
- CLI: available as `sclite` and `scl`.
- CI: GitHub Actions validation exists.
- PyPI publication target: `sclite-core==0.8.0a0` is the current alpha source/package candidate.

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

The `0.8.0-alpha` line keeps review-bundle behavior stable and removes the superseded proof-trace product path after consumer migration while preserving the no-runtime/no-PKI/no-adapter boundary. SCLite remains a local artifact validation and review package, not a policy authority or executor.
