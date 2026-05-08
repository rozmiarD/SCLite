# Changelog

## Unreleased

- Nothing yet.

## 0.2.1 - PyPI distribution rename

- Renames the PyPI distribution to `sclite-core` because PyPI does not allow the distribution name `sclite`.
- Keeps the Python import package as `sclite`.

## 0.2.0 - draft lifecycle candidate

- Introduces SCLite v0.2 as a contract lifecycle model from intent to evidence.
- Adds publication-readiness docs: `CONTRIBUTING.md`, `SECURITY.md`, `PUBLIC_STATUS.md`, and `VALIDATION.md`.
- Expands the publication checklist with Git identity, build/twine, clean-tree, version-decision, and explicit approval gates.
- Exposes `sclite.__version__` for package/version checks.
- Adds v0.2 schemas for `IntentContract`, `PolicyDecision`, `ExecutionContract`, `ExecutionTicket`, `ExecutionReceipt`, `EvidenceContract`, and `ArtifactChainManifest`.
- Adds lightweight cryptographic integrity primitives: canonical artifact descriptors and ordered SHA-256 hash-linked chain manifests.
- Adds `sclite validate-chain` and `sclite verify-lifecycle` for local verification of v0.2 lifecycle bundles.
- Adds semantic lifecycle verification for ticket/contract, receipt/ticket, evidence/receipt, role-order, and path-containment failures.
- Hardens the key v0.2 schemas around ticket approval/limits/validity/integrity, execution contract binding/shape/bounds, and evidence claims/replay/verification links.
- Adds a public-safe `contract-lifecycle-v0.2` fixture showing intent, policy, execution contract, integrity-bound ticket, receipt, evidence contract, and manifest verification.
- Keeps signer identity / PKI out of the core dependency path; v0.2 core verifies tamper-evident artifact binding only.

## 0.1.0 - draft candidate

- Initial SCLite package candidate.
- Adds schema-backed public-safe artifacts for the v0.1 proof trace.
- Adds draft `PreparedExecutionSpec` and `RedactedPreparedExecutionSpec` schemas and public-safe fixtures.
- Adds `sclite` CLI with fixture validation, artifact validation, Scope Fidelity reports, and validation receipts.
- Adds deterministic canonical JSON SHA-256 artifact hash helper and CLI.
- Adds `RedactionPolicy`, `RedactionReceipt`, `PublicValidationSurfaceIndex`, and `PublicSnapshotManifest` schemas, helpers, CLI surfaces, and fixtures.
- Adds synthetic public-safe examples and tests.
- Adds MIT license and package metadata for a future `pip install sclite` publication path.
