# SCLite Draft Specification

Status: **0.7.0-alpha review-lifecycle surface collapse**.
Current package release is `sclite-core==0.7.0a0`; the Python import package
remains `sclite`. The current front door is the review lifecycle substrate:
v0.2 lifecycle artifacts, v0.3 scoped ticket / receipt-bounded evidence checks,
and v0.5 review-bundle packaging. The 0.7 alpha line curates that substrate as
the root API and supports canonical review-bundle materialization for active
consumers without adding runtime, adapter, PKI, or policy authority.

Artifact schema versions and package release lines are different concepts. New
integrations should treat the lifecycle/review-bundle path as current. Legacy
v0.1 proof-trace artifacts remain compatibility/history material; Ravenclaw's
active path now consumes the current lifecycle/review-bundle front door.
SCLite is a schema-backed contract lifecycle and integrity/review layer. It is
not a scanner, executor, sandbox, policy engine, carrier protocol, or compliance
framework.

Core sentence:

> SCLite separates what an agent wants, what policy allows, what was approved, what was executed, and what can be proven.

## v0.2 Canonical Model

SCLite v0.2 models a governed action as an ordered artifact lifecycle:

```text
intent_contract -> policy_decision -> execution_contract -> execution_ticket -> execution_receipt -> evidence_contract -> artifact_chain_manifest
```

The lifecycle answers distinct questions:

- `intent_contract`: what did the agent/caller want?
- `policy_decision`: what did policy allow, deny, or require for review?
- `execution_contract`: what exact bounded execution shape was prepared?
- `execution_ticket`: what execution contract was approved, under what limits and validity window?
- `execution_receipt`: what did an external runtime report as executed or dry-run?
- `evidence_contract`: what public-safe claims/non-claims and replay checks can be reviewed?
- `artifact_chain_manifest`: does this local artifact bundle still match the ordered canonical digest chain?

The canonical fixture lives at `sclite/examples/contract-lifecycle-v0.2/` and is verified with:

```bash
sclite validate-chain sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json
sclite verify-lifecycle sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json
```

`verify-lifecycle` intentionally uses the same underlying verifier as `validate-chain`; it names the v0.2 reviewer intent more clearly.

## v0.2 Artifact Definitions

### IntentContract

Schema: `schemas/intent_contract.v0.2.schema.json`

Captures requested capability, target, actor/carrier context, constraints, and explicit authority boundaries. Intent is never execution authority.

### PolicyDecision v0.2

Schema: `schemas/policy_decision.v0.2.schema.json`

Captures the policy result and binds back to the intent descriptor. Typical decisions include allowing preparation, requiring owner approval, or denying the request. It does not implement policy itself.

### ExecutionContract

Schema: `schemas/execution_contract.v0.2.schema.json`

Captures the bounded execution shape to be reviewed/ticketed. Key required structures include:

- `target_binding`
- `execution_bounds`
- `execution_shape.tool`
- `execution_shape.normalized_args`

This is still only a contract; it does not execute anything.

### ExecutionTicket

Schema: `schemas/execution_ticket.v0.2.schema.json`

Captures approval for one exact execution contract. Key required structures include:

- `approval.status`
- `execution_limits.mode`
- `execution_limits.max_runs`
- `validity.not_before`
- `validity.not_after`
- `integrity.ticket_binds_execution_contract_digest`

The digest binding is mandatory. Signer identity / PKI remains out of core v0.2.

### ExecutionReceipt v0.2

Schema: `schemas/execution_receipt.v0.2.schema.json`

Captures a compact public-safe runtime receipt, including runtime mode, outcome summary, execution counts, and links back to the execution ticket/contract descriptors. Receipts summarize; they do not contain raw private logs.

### EvidenceContract

Schema: `schemas/evidence_contract.v0.2.schema.json`

Captures reviewer-facing claims, non-claims, replay mode, verification commands, and a required link to `links.execution_receipt`. Key required structures include:

- `claims`
- `non_claims`
- `replay`
- `verification`
- `links.execution_receipt`

### ArtifactChainManifest

Schema: `schemas/artifact_chain_manifest.v0.2.schema.json`

Captures the ordered tamper-evident digest chain over lifecycle artifacts. The manifest uses deterministic SCLite canonical JSON descriptors and hash-linked chain digests.

## v0.2 Integrity Chain

SCLite v0.2 verifies both structural chain integrity and lifecycle semantics:

1. every manifest entry path stays within the selected artifact root;
2. every artifact descriptor matches the canonical SHA-256 digest of the local JSON artifact;
3. every `previous_chain_digest` and `chain_digest` is recomputed in order;
4. the `root_chain_digest` matches the final recomputed chain digest;
5. the canonical lifecycle role order is enforced for v0.2 lifecycle manifests;
6. `policy_decision` binds the correct `intent_contract` digest;
7. `execution_contract` binds the correct intent and policy decision digests;
8. `execution_ticket` binds the correct `execution_contract` descriptor and `integrity.ticket_binds_execution_contract_digest`;
9. `execution_receipt` binds the correct `execution_ticket` and `execution_contract` digests;
10. `evidence_contract` binds the correct `execution_receipt` and `execution_ticket` digests.

This is lightweight cryptographic integrity, not identity trust. It proves the verifier saw the same canonical artifact bytes and lifecycle links; it does not prove who created them, whether a human was legally authorized, or whether a runtime enforced them.

## v0.3 Scoped Ticket Use

The `0.3.5` line includes the first scoped-ticket and receipt-bounded-evidence surfaces:

- `execution_ticket.v0.3` for runtime-consumable scoped-ticket artifacts;
- `sclite validate-ticket` and `sclite explain-ticket` for ticket review;
- `sclite verify-ticket-use` for static receipt/evidence checks against a scoped ticket, including explicit receipt-source binding and conservative completed-execution/network claim bounds.

These checks remain local artifact verification. They do not execute tools, decide authorization, prove signer identity, or attest that a runtime enforced a ticket.

## v0.4 Trust/Carrier References and Review Records

The `0.5.x` package line includes the v0.4-oriented trust/carrier and lifecycle-review surfaces:

- `trust_profile_ref.v0.1` and `sclite validate-trust-profile` validate digest-bound trust sidecars without proving signer identity, revocation, or PKI trust.
- `carrier_profile_ref.v0.1` and `sclite validate-carrier-profile` validate digest-bound carrier sidecars without proving delivery or adapter correctness.
- `scope_fidelity_report.v0.2`, `review_record.v0.1`, and `sclite review-lifecycle` summarize lifecycle review checks with conservative `pass` / `review` / `fail` verdicts.

These surfaces reserve stable vocabulary for external runtimes and verifiers. SCLite validates reference shape and local digest binding only.

## v0.5 Review Bundles

The `0.5.x` line adds a canonical review-bundle shape:

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

Review bundles are validated with:

```bash
sclite review examples/review-bundle --format json
sclite export-review-bundle examples/review-bundle --format markdown
```

`examples/govengine-integration/` is the 0.5.1 downstream fixture: it combines the canonical bundle shape with a v0.3 scoped ticket, receipt-bounded evidence, and trust/carrier sidecars for GovEngine consumption. `examples/bad-review-bundle-cross-host/` is an intentional negative fixture for cross-role target drift.

A bundle review emits a `review_record.v0.1` with conservative `pass` / `review` / `fail` verdicts. This is still static artifact review only: it does not execute tools, decide authorization, prove signer identity, or verify carrier delivery.

## Legacy v0.1 Compatibility

SCLite keeps the v0.1 public-safe proof trace as compatibility/history material
for existing Ravenclaw/public-proof migration. It is not the current front door
for new integrations:

```text
scope/input -> policy decision -> prepared execution spec -> approved execution spec -> dry-run execution receipt -> evidence summary
```

Legacy v0.1 artifacts remain schema-backed and useful for existing
Ravenclaw/public-proof migration:

- `PolicyDecision` v0.1
- `PreparedExecutionSpec`
- `RedactedPreparedExecutionSpec`
- `ApprovedExecutionSpec`
- `ExecutionReceipt` v0.1
- `EvidenceBundle`
- `RedactionPolicy`
- `RedactionReceipt`
- `PublicValidationSurfaceIndex`
- `PublicSnapshotManifest`
- `ScopeFidelityReport`
- `SecurityContractValidationReceipt`

v0.1 compatibility does not change the v0.2 canonical lifecycle. New work
should use the lifecycle/review-bundle model above. The `0.7.0-alpha` direction
is Ravenclaw-first surface collapse: migrate Ravenclaw off the legacy v0.1
front door, then retire v0.1 from the active SCLite integration contract rather
than preserving it as a permanent compatibility product.

## Non-Claims / Security Boundaries

SCLite core does **not** include:

- executors;
- scanners;
- sandboxing;
- `nmap`/`ffuf`/tool wrappers;
- agent loops;
- MCP/OpenClaw/A2A servers or adapters;
- authorization or ownership proof;
- live vulnerability proof;
- signer identity / PKI trust;
- a tamper-proof transparency log.

SCLite core capabilities are intentionally limited to:

```text
define / validate / hash / bind / redact / verify / review
```

Runtimes such as Ravenclaw may consume SCLite artifacts, enforce tickets, execute or dry-run tools, store raw evidence, and expose carrier adapters. Those responsibilities stay outside SCLite.

## Roadmap Boundary

Future SCLite work is expected to keep this split intact. Post-0.5 work should improve examples, failure drills, optional verifier integrations, and runtime handoff clarity while keeping policy decisions, trust decisions, live execution, revocation, raw evidence storage, and carrier adapter implementation outside SCLite core. See [`ROADMAP.md`](ROADMAP.md) for the versioned roadmap.
