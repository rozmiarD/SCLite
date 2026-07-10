# Changelog

## Unreleased

## 1.1.0rc1 - Strict JSON input policy candidate

- Adds closed-world `public_export` inventory for review bundles: unexpected,
  hidden, nested, case/Unicode-variant, symlink and special-file entries fail
  before export, while `local_review` reports inventory without claiming it is
  publication-safe.
- Materializes bundles through a same-parent stage, verifies and fsyncs the
  complete staged tree, then publishes by rename. Existing targets require an
  explicit `overwrite=True`, and failed replacement rolls the previous target
  back instead of leaving mixed contents.
- Adds the public `VerificationLimits` policy with finite per-file, aggregate,
  nesting, node-count and manifest-entry budgets.
- Routes production JSON file, inline, schema, manifest, Guard, review and
  public-snapshot reads through one strict loader that rejects duplicate object
  keys, non-standard `NaN`/`Infinity` values and invalid UTF-8.
- Applies one aggregate structure/byte budget to the manifest and artifacts of
  an artifact-chain verification while retaining explicit lower legacy CLI
  guards such as `--max-artifact-bytes`.

## 1.0.10rc1 - P0 verified-input and lifecycle hotfix candidate

- Uses one private immutable descriptor-verified snapshot for reaction,
  review, secure-bundle, ticket-use, and GovEngine handoff paths; payloads are
  not reopened after descriptor verification.
- Validates artifact-chain manifest identity, supported profile and declared
  signature policy before entries, and reports the verifier's actual
  canonicalization/hash policy rather than untrusted metadata.
- Fails explicit false scope assertions, keeps unknown scope/timestamps at
  review, and requires `not_before <= started_at <= ended_at <= not_after` for
  strict lifecycle and ticket-use pass paths.
- Keeps generic integrity available, but requires strict lifecycle pass for
  GovEngine lifecycle transitions. This candidate is unpublished; the latest
  published package remains `sclite-core==1.0.9`.

## 1.0.9 - Automation chain truth-layer artifact

- Added `automation_chain.v0.1` as the SCLite-owned multi-step automation-chain
  contract baseline, with public builders, schema validation, invariant
  verification, digest helper and tests for depth/reaction budgets, edge
  idempotency, GovEngine child admission, recovery policy and LLM proposal-only
  boundaries.
- published `sclite-core==1.0.9` package line as a truth-layer
  automation-chain artifact patch without adding runtime, policy, scheduler,
  connector, traversal, recovery, or domain ownership.

## 1.0.8 - Manual watchdog recovery context

- Extended `watchdog_decision.v0.1` with optional bounded
  `manual_recovery` context for GovEngine-admitted recovery/break-glass
  decisions. The context records actor reference, scope, human-signoff flag and
  reason without adding recovery authority, runtime supervision or policy
  decision ownership to SCLite.
- published `sclite-core==1.0.8` package line as a truth-layer
  manual-recovery-context patch without adding runtime, policy, scheduler,
  connector, recovery, or domain ownership.

## 1.0.7 - Watchdog decision truth-layer artifact

- Added the `watchdog_decision.v0.1` truth-layer artifact contract for bounded
  RExecOp runtime-supervisor decisions. It records watchdog observations,
  GovEngine admission and affected operation/event/inbox references without
  adding worker supervision, recovery authority, infrastructure monitoring,
  scheduler logic or execution ownership to SCLite.

## 1.0.6 - Trigger decision truth-layer artifact

- Added the `trigger_decision.v0.1` truth-layer artifact contract for bounded
  trigger/event decisions. It records event, rule-set, rule, GovEngine
  admission and optional child-operation references without adding trigger
  planning, policy authority, scheduler logic or execution ownership to SCLite.
- published `sclite-core==1.0.6` package line as a truth-layer trigger-decision
  artifact patch without adding runtime, policy, scheduler, connector, or domain
  ownership.

## 1.0.5 - Stack quality gates and typed package marker

- Added `ruff` to the development quality gate and published the PEP 561
  `py.typed` marker so downstream stack packages can type-check against SCLite.
- Corrected current GovEngine integration ranges to
  `sclite-core>=1.0.5,<1.1` and clarified that GovEngine owns governance while
  RExecOp or another host runtime owns execution.
- published `sclite-core==1.0.5` package line as a truth-layer packaging patch without
  adding runtime, policy, scheduler, connector, or domain ownership.

## 1.0.4 - Deterministic reaction evidence contracts

- published `sclite-core==1.0.4` package line for the reaction evidence boundary;
- added canonical `observation_envelope.v0.1`, `finding.v0.1`,
  `reaction_plan.v0.1`, and untrusted `escalation_proposal.v0.1` schemas;
- added builders, bounded reaction-chain verification, semantic digest links,
  stable idempotency keys, and tamper-detection tests;
- retained the SCLite boundary: no rule interpretation, policy authority,
  connector access, or runtime execution was added.

## 1.0.3 - Stable lifecycle and guarded verification surface

- published `sclite-core==1.0.3` package line as a stable SCLite audit roadmap
  v2 hardening patch after SCLite/GovEngine/Ravenclaw stack validation.
- Implements the 2026-06-14 audit roadmap v2 hardening without adding
  runtime, governance, replay-store, PKI/KMS, scanner, or raw-evidence scope.
- Makes generic `validate-chain` output explicit about
  `verification_posture=integrity_only` and `lifecycle_status=not_checked`,
  while preserving loose chain-validation compatibility.
- Runs real receipt-bounded `verify_ticket_use()` checks inside review records
  and guarded secure-bundle verification when v0.3 lifecycle artifacts are
  present.
- Adds strict/secure role-to-schema/version checks for canonical lifecycle
  roles without changing default loose `validate-chain` behavior.
- Adds a concrete host freshness handoff contract in docs while keeping replay
  storage and check-and-set outside SCLite.
- Extends the dependency-free schema subset for current packaged-schema
  keywords, adds parity/golden/generative tests, optional size guards, and an
  optional strict mypy experiment.

## 1.0.2 - Stable lifecycle and guarded verification surface

- published `sclite-core==1.0.2` package line as a stable SCLite roadmap
  hardening patch after SCLite/GovEngine/Ravenclaw stack validation.
- Adds explicit verifier layer statuses, fail-safe lifecycle verification,
  receipt/evidence compatibility checks, guarded-strict filesystem-boundary
  tests, and public-safe review-output disclosure coverage.
- Documents the schema-version compatibility matrix, unknown-field policy,
  artifact ID guidance, GovEngine downstream smoke, host freshness handoff,
  and post-1.0 release-readiness gates.
- Adds an opt-in package smoke for wheel/sdist build, `twine check`, clean
  wheel install, `pip check`, and `sclite-core` distribution import checks.

## 1.0.1 - Stable lifecycle and guarded verification surface

- published `sclite-core==1.0.1` package line as a stable SCLite security
  hardening patch after downstream GovEngine/Ravenclaw validation.
- Keeps `validate-chain` as integrity-only/generic chain verification by
  running lifecycle semantic checks only through `verify-lifecycle`,
  `validate-chain --strict-lifecycle`, or other `require_lifecycle=True`
  call paths.
- Hardens schema resolution so artifact-provided `schema_ref` values resolve
  to packaged SCLite schemas by default; external schema files now require
  explicit caller opt-in.
- Further tightens schema resolution so packaged schemas are accepted only via
  canonical ids, packaged filenames, or `schemas/<filename>` refs; path-like
  aliases do not match by basename, and explicit external schemas are resolved
  as one root-contained path with no repository fallback.
- Keeps Kernel Guard sidecar schema validation independent from artifact
  schema validation, so `--no-schema` cannot silently accept malformed guard
  sidecars.
- Registers the packaged `kernel_guard_hmac_v1` schema in the canonical schema
  registry and adds coverage that the registry matches packaged schema files.
- Strengthens the named GovEngine integration surface test with fixture-level
  API and CLI compatibility smokes.
- Makes repository gate scripts portable across environments that expose
  `python3` but not `python`.
- Adds a repository-local verification report for the 2026-06-01 external
  audit hypothesis.

## 1.0.0 - Stable lifecycle and guarded verification surface

- published `sclite-core==1.0.0` package line as the first stable SCLite
  release.
- Stabilizes the lifecycle/review and guarded verification surface introduced
  in `1.0.0rc1` without adding runtime, replay-store, PKI, KMS, policy, or
  carrier-adapter scope.
- Cleans up 1.0 release-candidate documentation truth around the retired
  proof-trace path and guarded sidecar examples.
- Adds shared JSON input handling so malformed local JSON files produce
  command-specific CLI failures instead of Python tracebacks.
- Adds `scripts/dev_gate.sh` and a small Makefile as the canonical local
  development validation gate.
- Documents and tests the frozen top-level Python public API surface for the
  1.0 line.

## 1.0.0-rc.1 - Guarded verification contract release candidate

- published `sclite-core==1.0.0rc1` package line as the first 1.0 release
  candidate.
- Adds `SECURITY_MODEL.md` and `docs/SECURITY_PROFILES.md` to freeze SCLite's
  security posture meanings for the 1.0 release-candidate path, including
  Kernel Guard transcript/canonicalization compatibility, replay ownership,
  key-rotation boundaries, and explicit non-claims.
- Adds `kernel_guard_hmac_v1` golden vectors to lock deterministic HMAC entry
  tags and root tag before the 1.0 release-candidate line.
- Adds a security regression gate for guarded-strict negative scenarios,
  including lifecycle injection, body/root/metadata tampering, guard transcript
  tampering, missing guard, and wrong-key failures.
- Adds the `verification_result.v1` contract so secure-bundle JSON output
  exposes artifact-chain, strict-lifecycle, Kernel Guard, replay, public
  identity, and runtime-enforcement statuses as machine-readable layer claims.
- Binds `entries[*].required` into the `kernel_guard_hmac_v1` per-entry HMAC
  transcript so guarded-strict verification rejects required-flag tampering
  without changing the historical artifact-chain digest algorithm.
- Validates Kernel Guard sidecar shape during verification, so schema drift and
  unexpected guard fields fail before transcript comparison.

## 0.8.0-beta - Lifecycle/review surface freeze

- Hardens lifecycle verification so `verify-lifecycle` requires the exact
  canonical v0.2 lifecycle role sequence and rejects extra roles, duplicate
  roles, and changed order instead of silently downgrading to hash-only chain
  validation or overwriting duplicate role entries during semantic checks.
- Adds optional `kernel_guard_hmac_v1` sidecar verification for
  GovEngine/KERNEL-domain authenticity over existing artifact-chain manifests,
  without mutating artifact bodies or adding runtime dependencies.
- Adds the fail-closed `verify-secure-bundle` / `guarded-strict` profile for
  runtime-consumable guarded bundles: strict lifecycle, artifact-chain
  verification, Kernel Guard HMAC verification, manifest metadata binding, and
  failure on missing guard. Existing review and chain commands also expose
  `--require-guard` / `--fail-on-unguarded` for explicit guard preflight.
- Corrects roadmap status language for the already published `0.8.0-alpha`
  line and adds public-truth coverage against reverting published current
  roadmap sections to candidate wording.
- Publishes the `sclite-core==0.8.0b2` package line by freezing
  the existing lifecycle/review front door and explicitly retaining current
  schema and fixture identifiers.
- Calibrates public package truth so README, status, and validation docs point
  at the published `sclite-core==0.8.0b2` package line.
- Removes current-documentation drift that described an active lifecycle
  negative fixture with retired prepared-execution wording or described a
  retained schema-level scoped-ticket artifact as a published package line.

## 0.8.0-alpha - Legacy proof-trace retirement

- Published the alpha package as `sclite-core==0.8.0a0` on PyPI.
- Removes the superseded proof-trace builders, fixture validator/receipt CLI, legacy-only schemas, and packaged fixtures after Ravenclaw migrated its current public proof projection.
- Keeps the lifecycle/review-bundle, scoped-ticket, receipt-bounded evidence, Scope Fidelity, redaction, and publication-hygiene contracts that remain in current use.
- Strengthens public truth validation so retired product surfaces cannot silently return as current package claims.

## 0.7.0-alpha - Ravenclaw-first surface collapse

- Promotes the candidate package line to `0.7.0a0` / `0.7.0-alpha` for Ravenclaw-first surface collapse.
- Adds canonical review-bundle materialization for runtime-produced current lifecycle artifacts.
- Curates the root API around current lifecycle/review, integrity, scoped-ticket, and scope-fidelity contracts; legacy v0.1 proof helpers remain explicit compatibility modules.
- Migrates the active Ravenclaw proof path to scoped-ticket lifecycle artifacts and review bundles without adding runtime, trust-authority, credential, or carrier ownership.
- Rejects lifecycle review manifest paths that escape the selected artifact root before artifact loading.
- Aligns generated lifecycle Scope Fidelity timestamps with their parent review records and adds tests that 0.6 alpha verification receipts match regenerated review records.
- Adds GitHub-compatible Mermaid diagrams to README and the lifecycle/runtime/review-bundle docs.
- Clarifies dependency-free schema validation as a documented subset and positions strict Draft 2020-12 validation as the CI/release authority.
- Adds a concrete threat model covering artifact tampering, runtime boundaries, Scope Fidelity limits, redaction limits, and PKI/non-authority boundaries.
- Requires canonical review-bundle sidecars (`REVIEW.md`, `verification_receipt.json`) during bundle-shape validation while still regenerating review output from source artifacts.
- Removes local absolute manifest paths from generated review records and adds tests for source-vs-packaged schema/review-fixture drift plus subset-vs-strict validator behavior.

## 0.6.0-alpha - Multi-runtime proof substrate

- Promotes the package line to `0.6.0a0` / `0.6.0-alpha`.
- Adds public truth validation for version, maturity, package badge/install, stable imports, validation gates, public fixtures, and non-authority boundaries.
- Adds `examples/local-admin-change/` as a second public-safe non-security review-bundle fixture plus packaged copy.
- Keeps SCLite limited to proof/review artifacts and does not add runtime execution, policy authority, PKI/KMS/key-store behavior, carrier adapters, or live infrastructure claims.

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
