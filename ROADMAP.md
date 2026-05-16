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

## Current baseline: 0.5.1

Current public package: `sclite-core==0.5.1`.

Current lifecycle:

```text
intent_contract -> policy_decision -> execution_contract -> execution_ticket -> execution_receipt -> evidence_contract -> artifact_chain_manifest
```

The v0.5.x line is the current review-bundle surface. The 0.5.1 patch freezes GovEngine integration imports/CLI semantics and adds downstream positive/negative review fixtures over SCLite's audit-proof lifecycle, scoped-ticket, receipt-bounded-evidence, trust/carrier reference, and lifecycle-review layers. It verifies schema-backed artifacts, canonical SHA-256 descriptors, ordered hash-chain manifests, lifecycle role order, digest bindings between intent, policy, execution contract, ticket, receipt, and evidence, and packaged reviewer-facing bundle output.

## Versioning discipline

Roadmap milestones use PEP 440-compatible package-style labels:

```text
0.2.5 -> 0.3.0 -> 0.3.5 -> 0.4.0 -> 0.4.5 -> 0.5.0 -> 0.5.1
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

Status: current patch line.

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

## Release posture

Do not rush a PyPI release for every roadmap milestone. A milestone should become a package release only when it adds real API, schema, CLI, or documentation value and passes the release checklist.

Before any tag/upload:

1. verify maintainer Git identity;
2. run full tests;
3. run lifecycle CLI validation;
4. validate v0.1 compatibility fixtures;
5. build package;
6. run `twine check`;
7. clean wheel install;
8. verify import and distribution versions;
9. obtain explicit operator approval;
10. upload;
11. verify PyPI JSON and clean install from PyPI.
