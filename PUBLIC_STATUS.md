# SCLite Public Status

SCLite is a lightweight Security Contract Layer lifecycle package.

## Current maturity

- Current package version: `0.3.5`.
- Status: published `0.3.x` scoped-ticket and receipt-bounded-evidence line.
- Runtime dependencies: none.
- CLI: available as `sclite` and `scl`.
- CI: GitHub Actions validation exists.
- PyPI publication: completed as `sclite-core==0.3.5`.

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

See `ROADMAP.md` for the planned progression beyond the current `0.3.5` scoped-ticket / receipt-bounded-evidence line toward trust/carrier profiles and review bundles. The first local trust/carrier profile reference checks have started as post-0.3.5 development work; they preserve the no-runtime/no-PKI/no-adapter boundary.
