# Changelog

## Unreleased

- Adds GitHub-compatible Mermaid diagrams to README and the lifecycle/runtime/review-bundle docs.
- Clarifies dependency-free schema validation as a documented subset and positions strict Draft 2020-12 validation as the CI/release authority.
- Adds a concrete threat model covering artifact tampering, runtime boundaries, Scope Fidelity limits, redaction limits, and PKI/non-authority boundaries.
- Requires canonical review-bundle sidecars (`REVIEW.md`, `verification_receipt.json`) during bundle-shape validation while still regenerating review output from source artifacts.
- Removes local absolute manifest paths from generated review records and adds tests for source-vs-packaged schema/review-fixture drift plus subset-vs-strict validator behavior.

## 0.5.1 - GovEngine integration readiness

- Freezes the documented GovEngine import/CLI contract for `sclite-core>=0.5.1,<0.6`.
- Adds `examples/govengine-integration/` as the downstream positive fixture with canonical review bundle, v0.3 scoped ticket, receipt-bounded evidence, and digest-bound trust/carrier sidecars.
- Adds `examples/bad-review-bundle-cross-host/` as an intentional negative fixture for cross-role target drift.
- Tightens lifecycle semantic verification so receipts bind both ticket and execution contract, and evidence binds both receipt and ticket.
- Adds CLI exit-code documentation plus public/strict validation gate scripts used by CI.
- Expands negative tests for review bundles, profile refs, scoped-ticket use, CLI failure modes, non-claims, and review-record contract shape.

## 0.5.0 - Review bundles

### Review bundles

- Publishes the SCLite review-bundle line as `sclite-core==0.5.0`.
- Added canonical `review_bundle/` validation with numbered lifecycle artifacts, `artifact_chain_manifest.json`, `REVIEW.md`, and `verification_receipt.json`.
- Added `sclite review` and `sclite export-review-bundle` for local review-bundle validation and Markdown export.
- Added packaged and source review-bundle fixtures while preserving conservative `pass` / `review` / `fail` verdicts.

### Trust and carrier profiles

- Includes the SCLite 0.4.0 trust/carrier profile line with digest-bound sidecar schemas: `trust_profile_ref.v0.1` and `carrier_profile_ref.v0.1`.
- Added `sclite validate-trust-profile` and `sclite validate-carrier-profile` to validate profile shape and subject-artifact digest binding only.
- Added public-safe fixtures and docs for trust/carrier references while preserving SCLite's no-PKI, no-trust-authority, no-adapter, and no-runtime boundary.

### Lifecycle review records

- Includes the SCLite 0.4.5 lifecycle-review line with `scope_fidelity_report.v0.2` and `review_record.v0.1` schemas.
- Added lifecycle-aware Scope Fidelity checks across intent, policy, execution contract, ticket, receipt, and evidence artifacts.
- Added `sclite review-lifecycle` to emit static public-safe lifecycle review records over artifact-chain manifests.
- Added public-safe lifecycle review fixtures and docs while preserving conservative `pass` / `review` / `fail` verdicts.

## 0.3.5 - Scoped tickets and receipt-bounded evidence

- Publishes the post-`0.2.1` scoped-ticket and receipt-bounded-evidence line as `sclite-core==0.3.5`.
- Preserves the Python import package as `sclite` and keeps runtime dependencies empty.

### Receipt-Bounded Evidence

- Started the `0.3.5` Receipt-Bounded Evidence line with `sclite verify-ticket-use`, scoped-ticket receipt/evidence fixtures, and static checks that receipt and evidence claims stay inside the ticket.
- Tightened `verify-ticket-use` so evidence claims must declare `source_receipt_id` and cannot claim completed execution, executed commands, or network execution beyond the linked receipt.
- Expanded README, integration guidance, and publication checklist coverage for scoped-ticket and receipt-bounded-evidence review commands.

### Scoped Tickets

- Started the `0.3.0` Scoped Tickets line with `execution_ticket.v0.3`, a public-safe scoped-ticket fixture, semantic ticket-to-contract checks, and `sclite validate-ticket` / `sclite explain-ticket`.

### Validation and roadmap hardening

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
