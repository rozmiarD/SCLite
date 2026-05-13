# SCLite v0.2 Draft Specification

Status: **published v0.2 draft lifecycle line**. Current package release is `sclite-core==0.2.1`; the Python import package remains `sclite`. SCLite is a schema-backed contract lifecycle and integrity layer. It is not a scanner, executor, sandbox, policy engine, carrier protocol, or compliance framework.

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
9. `execution_receipt` binds the correct `execution_ticket` digest;
10. `evidence_contract` binds the correct `execution_receipt` digest.

This is lightweight cryptographic integrity, not identity trust. It proves the verifier saw the same canonical artifact bytes and lifecycle links; it does not prove who created them, whether a human was legally authorized, or whether a runtime enforced them.

## Unreleased v0.3 Preview: Scoped Ticket Use

Local unreleased main includes the first scoped-ticket and receipt-bounded-evidence preview surfaces:

- `execution_ticket.v0.3` for runtime-consumable scoped-ticket artifacts;
- `sclite validate-ticket` and `sclite explain-ticket` for ticket review;
- `sclite verify-ticket-use` for static receipt/evidence checks against a scoped ticket, including explicit receipt-source binding and conservative completed-execution/network claim bounds.

These checks remain local artifact verification. They do not execute tools, decide authorization, prove signer identity, or attest that a runtime enforced a ticket.

## Legacy v0.1 Compatibility

SCLite keeps the v0.1 public-safe proof trace for compatibility:

```text
scope/input -> policy decision -> prepared execution spec -> approved execution spec -> dry-run execution receipt -> evidence summary
```

Legacy v0.1 artifacts remain schema-backed and useful for existing Ravenclaw/public-proof integrations:

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

v0.1 compatibility does not change the v0.2 canonical lifecycle. New v0.2 work should use the lifecycle model above.

## Non-Claims / Security Boundaries

SCLite v0.2 does **not** include:

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
define / validate / hash / bind / redact / verify
```

Runtimes such as Ravenclaw may consume SCLite artifacts, enforce tickets, execute or dry-run tools, store raw evidence, and expose carrier adapters. Those responsibilities stay outside SCLite.

## Roadmap Boundary

Future SCLite work is expected to keep this split intact. The planned direction is to make scoped execution tickets and receipt-bounded evidence more explicit while keeping policy decisions, trust decisions, live execution, revocation, raw evidence storage, and carrier adapter implementation outside SCLite core. See [`ROADMAP.md`](ROADMAP.md) for the versioned roadmap.
