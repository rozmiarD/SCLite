# Changelog

## Unreleased

- Added `ROADMAP.md` with PEP 440-compatible milestone labels for scoped tickets, receipt-bounded evidence, trust/carrier profiles, lifecycle review semantics, and review bundles.
- Linked the roadmap from public docs and clarified that future accountability-layer work remains artifact validation/review, not execution, policy authority, signer trust, or adapter implementation.
- Added optional strict Draft 2020-12 JSON Schema validation via `sclite-core[jsonschema]` and CLI `--strict-jsonschema`, while keeping the default validation path dependency-light.
- Added the v0.2 lifecycle chain validation and semantic `verify-lifecycle` commands to the documented publication validation gate, aligning SCLite docs with Ravenclaw reviewer demo usage.
- Cleaned README badge order, removed personal ownership copy from public-facing docs, and aligned `SPEC.md` status wording with the published `0.2.1` lifecycle line.
- Calibrated public docs after PyPI publication to reflect `sclite-core==0.2.1` as the install path and current release state.
- Clarified that `0.2.1` is a published draft lifecycle line, not an execution engine or adapter package.

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
- Adds MIT license and package metadata for a future PyPI publication path.
