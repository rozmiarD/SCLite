# Integration Guide

This guide is for runtimes, CLIs, CI jobs, or carrier adapters that want to use SCL artifacts.

SCLite v0.2 is centered on the contract lifecycle:

```text
intent_contract -> policy_decision -> execution_contract -> execution_ticket -> execution_receipt -> evidence_contract -> artifact_chain_manifest
```

SCL core is intentionally small. It provides schemas, validation helpers, redaction helpers, Scope Fidelity review, fixtures, lifecycle integrity verification, and a CLI. It does not provide a policy gateway, approval system, executor, sandbox, or carrier adapter.

## Recommended boundary

Keep these responsibilities outside SCL core:

- user/operator identity;
- scope program loading;
- policy evaluation;
- tool allowlists;
- approval authority;
- execution isolation;
- evidence storage;
- carrier transport;
- public publication flow.

Use SCL for the artifact boundary between those responsibilities.

## Reference flow

A governed runtime can use SCLite v0.2 like this:

1. **Receive intent**
   - Runtime receives a target/objective/task.
   - Runtime emits or maps that request into `IntentContract`.
   - Intent is not authority.

2. **Evaluate policy**
   - Runtime policy code decides whether preparing execution is allowed.
   - Runtime emits `PolicyDecision` v0.2 bound to the intent descriptor.

3. **Prepare execution contract**
   - Runtime compiles a concrete bounded execution shape.
   - Runtime emits `ExecutionContract` with target binding, tool, normalized args, and execution bounds.

4. **Approve execution ticket**
   - Reviewer/auditor/owner policy approves or rejects the execution contract.
   - Runtime emits `ExecutionTicket` bound to the exact execution contract digest, with approval status, validity, and execution limits.

5. **Execute or dry-run**
   - Runtime executor consumes its own approved/ticketed shape.
   - SCLite does not execute it.
   - Runtime emits `ExecutionReceipt` v0.2 bound to the ticket.

6. **Verify ticket use / evidence bounds**
   - For unreleased scoped-ticket fixtures, reviewers can run `sclite verify-ticket-use`.
   - The check verifies local bindings only: ticket/contract/receipt/evidence descriptors, runtime identity, mode, network flag, use count, explicit `source_receipt_id`, completed-execution claim bounds, and network/live claim bounds.
   - The check does not prove runtime enforcement, legal authorization, signer identity, or live vulnerability evidence.

7. **Emit evidence contract**
   - Runtime emits `EvidenceContract` with claims, non-claims, replay mode, verification commands, and a link to the receipt.
   - Claims that depend on a receipt should declare `bounded_by_receipt: true` and `source_receipt_id`.
   - Public outputs should keep raw private evidence elsewhere.

8. **Build and verify lifecycle chain**
   - Runtime builds `ArtifactChainManifest`.
   - CI/reviewer runs `sclite validate-chain` or `sclite verify-lifecycle`.
   - The verifier checks path containment, artifact digests, hash-chain links, role order, and the key lifecycle bindings.

Legacy v0.1 artifacts (`PreparedExecutionSpec`, `ApprovedExecutionSpec`, `ExecutionReceipt`, `EvidenceBundle`, and related public-safety artifacts) remain supported for compatibility and public proof traces.

## Minimal Python integration

Verify a v0.2 lifecycle bundle:

```python
from pathlib import Path

from sclite.integrity import verify_artifact_chain_manifest

# manifest is artifact_chain_manifest.json loaded as a dict.
result = verify_artifact_chain_manifest(manifest, root=Path("bundle-root"))
assert result["status"] == "passed"
assert "ticket_binds_execution_contract" in result["semantic_checks"]
```

Verify unreleased scoped-ticket use against receipt/evidence artifacts:

```python
from sclite.tickets import validate_ticket_semantics, verify_ticket_use

validate_ticket_semantics(ticket, execution_contract)
result = verify_ticket_use(ticket, execution_contract, execution_receipt, evidence_contract)
assert result["status"] == "passed"
assert "evidence_claims_bounded_by_receipt" in result["checks"]
```

## Carrier guidance

A carrier is anything that transports or triggers the workflow: a chat bot, OpenClaw plugin, MCP server, API endpoint, CI job, queue worker, or custom UI.

Good carrier behavior:

- preserve SCL artifacts as structured JSON;
- avoid flattening approvals into chat text only;
- keep non-claims visible;
- keep public-safe and private artifacts separated;
- require explicit approval before execution or publication;
- treat validation receipts as evidence of checks, not authorization.

Bad carrier behavior:

- treating a model message as executable authority;
- dropping target/scope facts;
- hiding approval source or constraints;
- publishing raw private evidence by default;
- claiming Scope Fidelity proves legal authorization;
- claiming a validation receipt authorizes public push.

## Endpoint shape for a future engine

A carrier-agnostic engine that consumes SCLite could expose endpoints such as:

- `POST /intent` -> `IntentContract`
- `POST /policy/decide` -> `PolicyDecision` v0.2
- `POST /execution/contract` -> `ExecutionContract`
- `POST /execution/ticket` -> `ExecutionTicket`
- `POST /execution/receipt` -> `ExecutionReceipt` v0.2
- `POST /evidence/contract` -> `EvidenceContract`
- `POST /artifacts/chain` -> `ArtifactChainManifest`
- `POST /artifacts/hash` -> canonical SHA-256 descriptor
- `POST /redaction/policy` -> `RedactionPolicy`
- `POST /redaction/receipt` -> `RedactionReceipt`
- `POST /public/validation-surface-index` -> `PublicValidationSurfaceIndex`
- `POST /public/snapshot-manifest` -> `PublicSnapshotManifest`

Those endpoints are not implemented in this repository. They are an integration direction for a separate engine package or runtime.

## Security notes

SCL validation is not enough for safe execution. A production system still needs real controls around:

- authentication and authorization;
- target/scope ownership;
- command construction;
- sandboxing;
- secrets management;
- output redaction;
- audit logging;
- rollback/kill switches;
- human approval gates.

SCL makes those controls easier to review because it gives them structured artifacts to produce and consume.
