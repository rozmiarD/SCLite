# SCLite Public Status

- Current source version: `2.0.1`.
- Source release label: `2.0.1`.
- Publication status: **published stable non-prerelease 2.0.1 release**.
- Latest published PyPI package: `sclite-core==2.0.1` (`2.0.1`).
- Python package: `sclite`.
- Python requirement: `>=3.11`.
- Runtime dependencies: none.
- Maturity classifier: `Development Status :: 4 - Beta`.

SCLite 2.0 is the stable, frozen contract/integrity/review kernel for the
current stack. It defines canonical lifecycle and evidence artifacts, verifies
digest and lifecycle bindings, supports scoped-ticket and receipt-bounded
evidence checks, produces review records, and verifies guarded bundles.

## Current ownership

```text
SCLite   truth contracts, canonicalization, integrity, review and verification
GovEngine governance, policy, admission, approvals, obligations and constraints
RExecOp  domain-neutral lifecycle, scheduling, connectors and execution
Profiles domain vocabulary, intent catalogs, workflows and validation
```

Reaction, trigger, watchdog and automation modules and schemas were removed
from SCLite 2.0. RExecOp owns those mechanics and historical artifact
resolution.

## Current public surface

- typed Python verification through `verify_artifact()` and `verify_bundle()`;
- canonical artifact descriptors and ordered lifecycle manifests;
- strict lifecycle and scoped-ticket verification;
- receipt-bounded evidence checks;
- review records and canonical review bundles;
- digest-bound trust/carrier references;
- Kernel Guard shared-secret verification;
- structured `verification_result.v1` and `verification_result.v1.1`;
- publication-hygiene records with explicit disclosure statuses;
- language-neutral conformance vectors;
- separate kernel (`sclite`, `scl`) and devtools (`sclite-devtools`) CLIs.

The superseded proof-trace product path and orchestration-specific 1.x surfaces
are absent from the installed package. Package history is retained in
[`CHANGELOG.md`](CHANGELOG.md) and
[`docs/archive/ROADMAP_VERSION_HISTORY.md`](docs/archive/ROADMAP_VERSION_HISTORY.md).

## Security posture

SCLite verifies only the layers selected by the caller. It reports unchecked
layers explicitly. Kernel Guard authenticates a transcript only within a
shared-secret domain; it is not PKI, public identity, non-repudiation or replay
protection.

The package does not claim:

- runtime execution or enforcement;
- governance or legal authorization;
- signer identity or trust-anchor validity;
- atomic replay protection or revocation;
- raw-evidence storage or truth;
- publication safety;
- production readiness for every possible host integration;
- Windows support for security-sensitive descriptor traversal/release tooling.

## Release posture

SCLite 2.0 is feature-frozen. Maintenance accepts documentation, validation,
test, packaging and compatibility corrections that do not widen ownership or
change frozen contract meanings. New schemas or public contracts require
demonstrated consumer need, an ownership review and an explicit release
decision.

The current `2.0.1` stable package includes release-tooling, documentation,
validation and test corrections while preserving the frozen 2.0 surface.
