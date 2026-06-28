# SCLite Roadmap

SCLite is a lightweight accountability layer for AI-assisted security and admin actions.

It binds intent, policy decisions, scoped execution tickets, runtime receipts, public-safe evidence, and integrity manifests into a verifiable lifecycle. It does **not** execute tools, decide trust, prove legal authorization, implement carrier adapters, or replace a policy/runtime engine.

Core positioning:

```text
AI can propose.
Scoped tickets bound what a runtime may consume.
Receipts bound what evidence may claim.
Review bundles make the lifecycle inspectable.
```

Ecosystem positioning:

```text
SCLite     = contract / proof / review layer
GovEngine  = deterministic governed-runtime kernel that consumes SCLite
Ravenclaw  = security-research runtime/profile over GovEngine + SCLite
Tecrax     = future infrastructure-operations runtime/profile over GovEngine + SCLite
```

SCLite must stay deliberately small. The emergence of GovEngine as a broader governed-runtime kernel and Tecrax as a second domain profile is a reason to keep SCLite narrower, not broader.

## Current baseline: 1.0.6

Current package: `sclite-core==1.0.6`.
Latest published public package: `sclite-core==1.0.5`.

Roadmap v2 hardening from the 2026-06-14 audit was implemented in `1.0.3`.
The `1.0.4` patch extends only the truth-layer boundary with versioned reaction
artifacts and replayable digest links; deterministic interpretation remains in
RExecOp, governance remains in GovEngine, and domain semantics remain in the
profile.
The `1.0.5` patch keeps that boundary unchanged and publishes only packaging
truth: PEP 561 typing metadata plus repository quality gates.
The `1.0.6` source line adds a narrow `trigger_decision.v0.1` truth-layer
artifact for RExecOp trigger/event decisions. It records bounded event, rule,
GovEngine admission and optional child-operation references; trigger matching,
planning, policy and execution remain outside SCLite.

Current lifecycle:

```text
intent_contract -> policy_decision -> execution_contract -> execution_ticket -> execution_receipt -> evidence_contract -> artifact_chain_manifest
```

The v0.5.x line remains the stable review-bundle shape. The 1.0 stable
release freezes the lifecycle/review-bundle path as the single curated front
door, includes the deterministic review-bundle materializer used by active
consumers, retains the alpha removal of the superseded proof-trace product path
after controlled consumer migration, and stabilizes guarded verification
evidence: security profile docs, Kernel Guard golden vectors,
security regression gate, `verification_result.v1`, clean CLI input failures,
the canonical developer gate, and the frozen top-level public API. It verifies
schema-backed artifacts, canonical SHA-256 descriptors, ordered hash-chain
manifests, lifecycle role order, digest bindings between intent, policy,
execution contract, ticket, receipt, and evidence, and packaged
reviewer-facing bundle output without adding runtime, adapter, PKI, or policy
authority.

## Completed 2026-06-14 audit roadmap v2 hardening

The audit roadmap v2 is delivered as narrowly scoped truth-layer work:

1. `validate-chain` reports integrity-only posture unless strict lifecycle is
   requested.
2. Review records and guarded secure-bundle verification run the existing
   `verify_ticket_use()` receipt-bounded evidence gate when v0.3 artifacts are
   present.
3. Strict lifecycle and guarded/secure profiles enforce lifecycle
   role-to-schema/version identity while loose chain validation stays
   compatibility-preserving.
4. GovEngine/Tecrax freshness handoff is documented as a host-owned replay
   contract, not as a SCLite replay DB.
5. Schema-mode parity, golden output, generated invariant, and optional size
   guard tests cover the new contract surface.

Still out of scope: runtime execution, planning, orchestration, governance
policy decisions, replay check-and-set state, PKI/KMS, scanners, and raw
evidence storage.

## Completed 0.8 beta hardening: strict lifecycle and optional kernel guard

The 0.8 beta hardening step was intentionally ordered and is now implemented:

1. make lifecycle verification fail closed for non-canonical lifecycle role
   lists;
2. document integrity-only limits and signature-policy non-claims;
3. add an optional `kernel_guard_hmac_v1` manifest/sidecar guard only after the
   lifecycle verifier is strict.

Strict lifecycle means exactly this role sequence and no extras or duplicates:

```text
intent_contract -> policy_decision -> execution_contract -> execution_ticket -> execution_receipt -> evidence_contract
```

Generic chain validation may remain useful for non-lifecycle hash-chain
manifests, but `verify-lifecycle` must not silently downgrade to hash-only
validation when a lifecycle-shaped manifest carries extra roles, duplicate
roles, or changed order.

The `kernel_guard_hmac_v1` profile is optional and lightweight. It binds
existing manifest entries and descriptors through a sidecar guard, not by
mutating each artifact body. It may provide authenticity inside a
GovEngine/KERNEL domain that knows the HMAC secret; it must not claim public
PKI, global identity, non-repudiation, replay prevention without a GovEngine
replay store, or protection from a malicious kernel.

## Versioning discipline

Roadmap milestones use PEP 440-compatible package-style labels:

```text
0.2.5 -> 0.3.0 -> 0.3.5 -> 0.4.0 -> 0.4.5 -> 0.5.0 -> 0.5.1 -> 0.6.0a0 -> 0.7.0a0 -> 0.8.0a0 -> 0.8.0b2 -> 1.0.0rc1 -> 1.0.0 -> 1.0.1 -> 1.0.2 -> 1.0.4 -> 1.0.5 -> 1.0.6
```

Avoid non-monotonic labels such as `0.25`: under PEP 440, `0.25` sorts after `0.5`, which is not the intended roadmap order. Not every roadmap milestone has to become a PyPI release, but release versions must remain monotonic and PEP 440-compatible.

## Ownership boundary

SCLite owns:

- artifact schemas;
- deterministic canonicalization and digest descriptors;
- lifecycle integrity verification;
- local/public-safe fixture validation;
- redaction trace artifacts;
- Scope Fidelity review artifacts;
- reviewer-facing CLI surfaces.

SCLite does not own:

- live execution;
- scanners or tool wrappers;
- policy engines;
- approval authority;
- signer/PKI trust decisions;
- protocol/carrier adapters;
- raw evidence storage;
- runtime orchestration.

GovEngine or another runtime may consume SCLite artifacts and decide policy, trust, approval, execution, revocation, and runtime enforcement. Ravenclaw is the reference security runtime/proof implementation in the current project family; Tecrax is the reserved name for a future governed infrastructure-operations runtime/profile.

Boundary invariant:

```text
SCLite defines and verifies proof artifacts.
SCLite does not decide whether the world may be changed.
```

## 0.2.5 — Baseline discipline and strict validation bridge

Goal: make the current boundary unambiguous and prepare stricter validation without adding default runtime dependencies.

Planned work:

1. Publish this roadmap and link it from public docs.
2. Clarify that SCLite does not govern agents; it bounds side effects by making scoped execution and evidence claims reviewable.
3. Add a lifecycle/version compatibility table for v0.1, v0.2, v0.3, and v0.5 surfaces.
4. Add an optional strict Draft 2020-12 JSON Schema validation path, for example:

   ```bash
   pip install 'sclite-core[jsonschema]'
   sclite validate-artifact --strict-jsonschema --schema ... artifact.json
   ```

5. Keep the default core lightweight and dependency-minimal.
6. Add or tighten source-vs-packaged schema parity tests.

Status as of the post-0.5.1 documentation hardening pass: strict validation, subset-vs-strict tests, source-vs-packaged schema/review-fixture drift tests, threat-model docs, and Mermaid architecture diagrams are implemented. Remaining candidates for a future release are CLI modularization, a manually curated public `__all__`, and broader property-based tests for host extraction, canonical JSON, descriptor mismatch, path traversal, and digest drift.

Validation gate:

- `python -m pytest -q`
- `python -m sclite.cli validate-chain sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json`
- `python -m sclite.cli verify-lifecycle sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json`
- v0.1 compatibility fixture validation
- documentation/link checks for touched files

## 0.3.0 — Scoped Tickets

Status: published in `0.3.5`. The implementation adds `execution_ticket.v0.3`, a public-safe scoped-ticket fixture, static ticket-to-contract semantic validation, and reviewer-facing ticket CLI commands.

Goal: make `ExecutionTicket` explicitly runtime-consumable while preserving SCLite's non-authority boundary.

An ExecutionTicket should become a **Scoped Ticket**: a bounded ticket a runtime can consume before side effects. It is not legal authorization, signer trust, or proof of runtime enforcement by itself.

Planned work:

1. Add `execution_ticket.v0.3.schema.json`.
2. Define ticket profiles:
   - `review_record`
   - `scoped_execution_ticket`
   - `external_capability_ref`
3. Add first-class ticket-consumption fields such as:
   - `ticket_profile`
   - `ticket_semantics`
   - `subject_binding`
   - `scope_binding`
   - `spend_limits`
   - receipt/evidence obligations
4. Verify that ticket scope, tool, mode, normalized argument digest, and spend limits match the execution contract.
5. Add reviewer-facing CLI:

   ```bash
   sclite validate-ticket execution_ticket.json
   sclite explain-ticket execution_ticket.json
   ```

Key negative tests:

- target drift;
- mode escalation;
- tool drift;
- normalized-argument digest mismatch;
- unsupported runtime-consumption profile;
- `review_record` ticket treated as runtime-consumable.

## 0.3.5 — Ticket-use semantics and receipt-bounded evidence

Status: published in `0.3.5`. The implementation adds `sclite verify-ticket-use` and a scoped-ticket receipt/evidence fixture with static checks for receipt-to-ticket binding, runtime/mode/network/use limits, explicit `source_receipt_id`, receipt-bounded evidence claims, completed-execution/network claim bounds, and replay limits.

Goal: add the strongest downstream invariant:

> Evidence claims must be receipt-bounded.

A public-safe evidence contract should not claim more than the execution receipt supports.

Planned work:

1. Strengthen `ExecutionReceipt` semantics around runtime identity, mode, observed run count, network execution, and blocked/rejected outcomes.
2. Add ticket-use verification:

   ```bash
   sclite verify-ticket-use execution_ticket.json --contract execution_contract.json --receipt execution_receipt.json --evidence-contract evidence_contract.json
   ```

3. Add receipt-bounded evidence verification as either a standalone command or a stricter profile layered on `verify-ticket-use`.

4. Enforce rules such as:
   - dry-run receipts cannot support live vulnerability claims;
   - blocked/rejected receipts cannot support completed-execution claims;
   - `network_execution_performed=false` cannot support live network-execution claims;
   - evidence without a receipt cannot claim execution truth.

This milestone is the main accountability upgrade: SCLite should prevent AI-assisted reports from claiming more than the scoped execution record supports.

## 0.4.0 — Trust and Carrier Profiles

Status: published in `0.5.0`. The implementation adds digest-bound `trust_profile_ref.v0.1` and `carrier_profile_ref.v0.1` sidecars, fixtures, docs, and CLI checks.

Goal: define how SCLite artifacts can be signed, transported, and externally verified without making SCLite a PKI, adapter, or trust authority.

This milestone should support GovEngine and future domain runtimes such as Ravenclaw and Tecrax by binding trust/carrier references to artifact digests. It should not add runtime adapters or trust decisions to SCLite.

Principle:

```text
SCLite artifacts are payloads.
Carrier profiles describe transport.
Trust profiles describe signature/reference expectations.
External verifiers decide trust.
```

Planned work:

1. Add `docs/TRUST_PROFILES.md` with profiles such as:
   - `none`
   - `digest_only`
   - `local_ed25519_ref`
   - `dsse_envelope_ref`
   - `sigstore_bundle_ref`
   - `external_verifier`
2. Add `docs/CARRIER_PROFILES.md` with profiles such as:
   - `local_file_bundle`
   - `ci_artifact_bundle`
   - `github_artifact`
   - `govengine_bundle`
   - `ravenclaw_review_bundle`
   - `tecrax_review_bundle`
   - `openclaw_carrier_payload`
   - `mcp_message_ref`
   - `a2a_message_ref`
3. Validate presence, placement, and digest binding of trust references only.
4. Keep DSSE/Sigstore verification outside default core unless a later optional verifier profile is explicitly added.
5. Document the in-toto-like mental model without claiming SCLite replaces in-toto.

## 0.4.5 — Lifecycle review semantics and Scope Fidelity v0.2

Status: published in `0.5.0`. The implementation adds `scope_fidelity_report.v0.2`, `review_record.v0.1`, lifecycle review records, fixtures, docs, and `sclite review-lifecycle`.

Goal: prepare the review-bundle surface by making lifecycle-level review semantics precise.

Planned work:

1. Add lifecycle-aware Scope Fidelity, likely as `scope_fidelity_report.v0.2.schema.json`.
2. Compare target references across:
   - intent;
   - policy decision;
   - execution contract;
   - scoped ticket;
   - execution receipt;
   - evidence contract.
3. Preserve conservative verdicts:
   - `pass`
   - `review`
   - `fail`
4. Draft a review result shape that aggregates schema validation, chain integrity, lifecycle binding, scoped ticket semantics, ticket use, receipt-bounded evidence, Scope Fidelity, trust/carrier profile checks, failure catalog entries, and non-claims.

## 0.5.0 — Review Bundles and adoption demos

Status: published in `0.5.0`. The implementation adds canonical review-bundle validation/export, packaged/source fixtures, docs, and CLI commands `sclite review` and `sclite export-review-bundle`.

Goal: make SCLite understandable, demoable, and adoptable without Ravenclaw.

Canonical review bundle shape:

```text
review_bundle/
  01_intent_contract.json
  02_policy_decision.json
  03_execution_contract.json
  04_execution_ticket.json
  05_execution_receipt.json
  06_evidence_contract.json
  artifact_chain_manifest.json
  REVIEW.md
  verification_receipt.json
```

Implemented CLI:

```bash
sclite review examples/review-bundle --format json
sclite export-review-bundle examples/review-bundle --format markdown
```

Implemented example:

```text
examples/review-bundle/
```

Candidate post-0.5 examples:

```text
examples/integrity-drills/
examples/ci-dry-run/
examples/local-admin-change/
examples/security-review-without-runtime/
examples/govengine-compatible-runtime-stub/
examples/tecrax-local-admin-change/
```

Integrity drill examples should demonstrate concrete failure modes:

- target drift;
- dry-run to live mode escalation;
- tool drift;
- evidence overclaim;
- missing receipt;
- expired ticket.

A key non-scanner example should be an AI-proposed firewall rule change: SCLite can show intent, policy review, exact dry-run config validation, scoped ticket, receipt, evidence, and manifest without requiring Ravenclaw or a live security scan.

## 0.5.1 — GovEngine integration readiness

Status: published predecessor patch line.

Goal: make the SCLite 0.5 surface safe and boring for GovEngine to consume before package-chain sync.

Implemented scope:

- documented stable import and CLI contract for `sclite-core>=0.5.1,<0.6`;
- documented CLI exit-code semantics for CI and downstream gates;
- added `examples/govengine-integration/` as the positive downstream fixture;
- added `examples/bad-review-bundle-cross-host/` as an intentional negative fixture;
- tightened lifecycle semantic verification for receipt-to-contract and evidence-to-ticket links;
- added public/strict validation scripts and wired CI to them;
- expanded negative tests for bundles, profile refs, ticket use, CLI behavior, and public non-claims.

This patch does not add runtime execution, policy authority, trust decisions, or carrier adapters. It only clarifies and hardens the review/proof substrate that GovEngine may consume.

## 0.6.0-alpha — Multi-runtime proof substrate

Status: delivered predecessor line.

Goal: make SCLite credible as a dependency-light proof/review substrate for
more than one governed runtime without widening its authority.

Implemented scope:

- public truth validator for version, maturity, package badge/install, docs, stable imports, validation gates, public fixtures, and non-authority boundaries;
- exact alpha package badge/install truth for `sclite-core==0.6.0a0`;
- `examples/local-admin-change/` and packaged copy as a second non-security review-bundle fixture over the same lifecycle;
- public validation surface index includes the local-admin-change review bundle;
- review-bundle and packaged-fixture tests cover the new fixture.

This alpha does not add runtime execution, policy decisions, trust decisions,
PKI/KMS/key-store behavior, carrier adapters, live infrastructure operations,
or legal authorization claims.

## 0.6.x — Alpha substrate stabilization

Goal: keep the new multi-runtime proof claim boring before adding another
artifact or schema family.

The 2026-05-23 surface audit changes the next decision: SCLite should not keep
expanding or preserving broad compatibility by default. Its only real consumers
are GovEngine, Ravenclaw indirectly, and Tecrax's dry-run/local-fixture pressure
surface. That makes uncontrolled compatibility preservation more expensive than
useful during alpha development.

Next work should consolidate what already exists:

1. keep `examples/govengine-integration/` and `examples/local-admin-change/`
   equivalent at the review-bundle contract level while preserving their
   different domain stories;
2. add or tighten failure-catalog coverage for review bundles, lifecycle
   binding drift, scoped-ticket misuse, receipt-bounded evidence overclaims,
   and trust/carrier reference digest drift only where current fixtures leave a
   real gap;
3. make source fixture, packaged fixture, CLI summary, and review-record
   outputs stay mechanically aligned;
4. document compatibility expectations for the stable 0.5 review-bundle
   surface consumed by GovEngine and Ravenclaw;
5. keep the dependency-light validator and optional strict JSON Schema path
   behaviorally aligned for supported fixtures;
6. identify which current imports are truly consumed by GovEngine, Ravenclaw,
   and Tecrax, and treat everything else as internal or compatibility-only
   unless a test proves otherwise;
7. stop presenting legacy v0.1 proof-trace artifacts as a current front door for
   new integrations.

Success criteria:

- public and strict validation gates pass for both public-safe review-bundle
  families and the intentional negative fixture;
- GovEngine still consumes the SCLite package through review-bundle and
  scoped-ticket boundaries without private fixture knowledge;
- the second non-security fixture proves portability without adding runtime,
  policy, credential, trust-authority, or adapter claims;
- public truth, package data, fixture sync, and CLI exit-code tests reject
  documentation or packaged-fixture drift;
- SCLite has a concrete `0.7.0-alpha` cleanup plan before any new schema family
  is added.

## 0.7.0-alpha — Ravenclaw-first surface collapse and legacy retirement

Status: published predecessor migration line.

Do not open a 0.7 schema wave merely because GovEngine or Ravenclaw is moving.
The next minor line is justified only as a cleanup/boundary release: reduce the
active SCLite public surface to what current consumers actually use, migrate
Ravenclaw off the legacy v0.1 proof front door, retire legacy from the active
integration contract, and separate package release labels from artifact schema
versions.

Problem statement:

- README and docs currently describe `v0.1`, `v0.2`, `v0.3`, `v0.4`, `v0.5`,
  and `v0.6` in one product narrative. In code these are mixed concepts:
  artifact schema versions, package milestones, compatibility fixtures, and
  review-bundle packaging.
- SCLite has no uncontrolled external consumer base that requires preserving all
  active surfaces during alpha development.
- Ravenclaw is an active controlled consumer, so preserving legacy v0.1 mainly
  for Ravenclaw would manufacture long-term support cost. The better path is to
  migrate Ravenclaw first, then simplify SCLite.
- The broad `sclite.__all__` export makes accidental helpers look public.
- `SPEC.md` and some docs can drift because public truth validation does not yet
  cover every current-claim document.

Target current front door:

- canonical review lifecycle artifacts and artifact-chain verification;
- canonical review-bundle validation/export;
- scoped-ticket and receipt-bounded-evidence verification needed by GovEngine;
- digest-bound trust/carrier reference validation only as static references;
- deterministic artifact descriptors and dependency-free/strict validation
  paths;
- public truth and fixture/package parity validators.

Ravenclaw migration target:

- Ravenclaw's active proof/security-contract validation path should use the
  current SCLite lifecycle/review-bundle path instead of the legacy v0.1 proof
  trace.
- Ravenclaw must be migrated away from wildcard `sclite.artifacts` consumption.
- v0.1 public proof trace, prepared/approved spec helpers, legacy evidence
  bundle helpers, and validation receipt helpers should become historical or
  temporary migration-only support, not a permanent compatibility product.

Required work:

1. Replace broad `sclite.__all__` generation with a curated public export list.
2. Add a public surface validator that fails when undocumented helpers are
   exported as current API.
3. Extend public truth validation to cover `SPEC.md`, `docs/ARTIFACTS.md`, and
   any document that claims the current SCLite front door.
4. Update README/PUBLIC_STATUS/SPEC/ROADMAP/VALIDATION wording so package lines
   and artifact schema versions are not presented as competing product versions.
5. Patch Ravenclaw first so its current path consumes lifecycle/review-bundle
   outputs and no longer treats v0.1 proof helpers as active SCLite surface.
6. Keep any v0.1 support only as temporary migration scaffolding until
   Ravenclaw, GovEngine, and Tecrax tests are green against the narrowed
   surface.
7. Add downstream conformance tests for the exact imports GovEngine, Ravenclaw,
   and Tecrax use.
8. Keep all compatibility breakage explicit: no silent removal before the
   dependent repos are patched and validated.

Delivered in `0.7.0-alpha`:

- `sclite.__all__` is curated around current lifecycle/review, integrity,
  scoped-ticket, and scope-fidelity surfaces instead of re-exporting legacy
  proof helpers;
- `sclite.bundles.materialize_review_bundle()` packages runtime-produced
  lifecycle artifacts into the canonical locally reviewable bundle shape;
- Ravenclaw's active demo/current lifecycle path produces a scoped-ticket
  lifecycle and canonical review bundle; explicit v0.1 helpers remain only for
  compatibility fixtures and migration tests;
- public truth validation checks the curated root export boundary and the
  GovEngine import contract.

Success criteria:

- SCLite still owns proof/review artifacts only;
- GovEngine and Ravenclaw can validate the new surface without live execution,
  credentials, network targets, or protocol adapters;
- Tecrax still needs no more than the neutral descriptor/review fixture path;
- Ravenclaw's active proof path no longer depends on legacy v0.1 as the current
  SCLite integration contract;
- docs name one current SCLite front door and classify legacy v0.1 as
  historical or temporary migration support;
- broad legacy surfaces are not advertised as current integration APIs;
- validators mechanically reject reintroducing stale current claims;
- existing review-bundle consumers remain compatible or receive an explicit
  migration contract before release.

Out of scope:

- new runtime behavior;
- new policy/trust authority;
- OpenClaw/MCP/A2A adapters;
- PKI/KMS/key-store behavior;
- new schema families not required to complete the surface collapse.

## 0.8.0-alpha — Retire superseded proof-trace product path

Status: published current alpha line after Ravenclaw consumer migration.

Delivered:

1. Remove `sclite.validation`, proof-trace builders/invariants, and the
   `sclite validate` / `sclite validation-receipt` legacy CLI path.
2. Remove legacy-only proof fixtures and schemas from source and packaged data.
3. Keep current lifecycle/review schemas and independently used static
   Scope Fidelity, redaction, snapshot, and review-record formats.
4. Require public truth validation to fail if retired paths, CLI commands, or
   schemas reappear as installed/current product surfaces.
5. Preserve the boundary: no runtime execution, policy authority, adapter,
   PKI/KMS, or key-store behavior is introduced.

Success criteria:

- Ravenclaw current proof projection validates only through the current
  lifecycle/review-bundle path;
- GovEngine uses only the documented neutral SCLite import surface;
- source and packaged SCLite no longer contain the retired proof-trace product
  directories, validators, or owned-only schemas;
- public, strict-schema, pytest, clean-wheel, and downstream compatibility
  gates passed for the published `0.8.0-alpha` line.

## 0.8.0-beta — Freeze lifecycle/review public responsibility

Status: published predecessor beta line.

Candidate scope:

1. Freeze the existing lifecycle/review-bundle front door, stable GovEngine
   imports and explicit non-claims for the beta line.
2. Preserve retained schema and fixture identifiers that describe current
   contracts; do not turn cosmetic renaming into artifact churn.
3. Keep runtime execution, policy authority, adapter, PKI/KMS, storage and
   production-readiness behavior outside SCLite.
4. Require validation to keep current package truth aligned with the published
   beta line.
5. Prove GovEngine, Ravenclaw and Tecrax consumption without adding SCLite
   surface breadth.

## 1.0.0-rc.1 — Freeze guarded verification contracts

Status: published predecessor release candidate.

Delivered:

1. Freeze `SECURITY_MODEL.md` and `docs/SECURITY_PROFILES.md` as the public
   security posture and non-claim contract.
2. Add `kernel_guard_hmac_v1` golden vectors for deterministic entry tags and
   root tag.
3. Add a CI-backed security regression gate for guarded-strict negative
   scenarios.
4. Add `verification_result.v1` so secure-bundle JSON output exposes
   artifact-chain, strict-lifecycle, Kernel Guard, replay, public-identity, and
   runtime-enforcement statuses as machine-readable claims/non-claims.
5. Preserve SCLite's no-runtime, no-replay-store, no-PKI, no-KMS, and
   no-carrier-adapter boundary.

## 1.0.0 — Stable lifecycle/review and guarded verification surface

Status: published current stable release.

Delivered:

1. Promote the guarded verification contract from RC to stable without adding
   runtime, replay-store, PKI, KMS, policy, or carrier-adapter scope.
2. Preserve strict lifecycle, `kernel_guard_hmac_v1` sidecar verification,
   golden vectors, security regression gate, and `verification_result.v1`.
3. Add clean CLI input failures for malformed local JSON/path inputs so users
   receive labeled command errors instead of tracebacks.
4. Add `scripts/dev_gate.sh` and `make validate` as the canonical local
   development gate.
5. Freeze the top-level Python public API in `docs/PUBLIC_API.md` with a
   regression test.

## Release posture

Do not rush a PyPI release for every roadmap milestone. A milestone should become a package release only when it adds real API, schema, CLI, or documentation value and passes the release checklist.

Before any tag/upload:

1. verify maintainer Git identity;
2. run full tests;
3. run lifecycle CLI validation;
4. confirm retired proof-trace paths and CLI commands remain absent;
5. build package;
6. run `twine check`;
7. clean wheel install;
8. verify import and distribution versions;
9. obtain explicit operator approval;
10. upload;
11. verify PyPI JSON and clean install from PyPI.
