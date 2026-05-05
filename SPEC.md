# SCLite / Security Contract Layer v0.1 Draft Spec

Status: **draft v0.1**. This document describes the current package and schema bundle. It is not a standard, protocol, or compliance framework.

SCL defines schema-backed artifacts for governed security/agentic execution. The intended use is to keep proposal, policy, approval, execution shape, receipts, and evidence separate enough to review and validate.

## Design principles

1. **Intent is not authority.** A model/tool caller proposing an action is not the same as an approved executable contract.
2. **Approval should bind to execution shape.** Reviewers should see what target/tool/arguments/plan are being approved.
3. **Receipts should be compact and public-safe by default.** Raw evidence can live elsewhere; public proof artifacts should state what they do and do not claim.
4. **Validation should be local and reproducible.** Fixtures should be checkable without live target execution.
5. **Carriers are separate.** Chat systems, MCP servers, OpenClaw plugins, CI jobs, or custom runtimes can carry SCL artifacts, but SCL does not replace those systems.

## Canonical proof trace

```text
scope/input -> policy decision -> prepared execution spec -> approved execution spec -> dry-run execution receipt -> evidence summary
```

The current fixture directory `examples/security-contract-proof/` contains this public-safe chain:

- `policy_decision.json`
- `prepared_execution_spec.redacted.json`
- `approved_execution_spec.json`
- `execution_receipt.json`
- `evidence_bundle.json`
- `evidence_summary.md`

## Artifact definitions

### PolicyDecision

Schema: `schemas/policy_decision.v0.1.schema.json`

Purpose: capture the result of a policy/scope/tooling decision before a concrete execution contract is approved.

Current decisions:

- `allow_prepare`
- `owner_approval_required`
- `deny`

Current limitations:

- does not prove legal authorization;
- does not define a full policy engine;
- does not cryptographically bind to later artifacts.

### PreparedExecutionSpec / redacted prepared spec

Current fixture: `prepared_execution_spec.redacted.json`

Purpose: show a public/auditor-safe view of a prepared execution shape before approval.

Current status:

- represented in fixtures;
- generic redaction helper exists;
- no dedicated v0.1 schema in this package yet.

Current limitations:

- redaction is conservative but not a complete secret scanner;
- this package does not build runtime-specific prepared specs;
- runtime-specific redaction can be stronger than SCL's generic helper.

### ApprovedExecutionSpec

Schema: `schemas/approved_execution_spec.v0.1.schema.json`

Purpose: describe the approved execution shape a governed runtime may consume.

Important fields include:

- `spec_version`
- `target`
- `target_host`
- `target_in_scope`
- `resolved_tool`
- `normalized_args`
- `execution_plan`
- `scope_facts`
- `approval`
- `execution_truth`

Current limitations:

- SCL validates shape; it does not execute the spec;
- SCL does not enforce runtime-wide mandatory execution through this path;
- v0.1 has no signature/hash-chain binding to previous artifacts.

### ExecutionReceipt

Schema: `schemas/execution_receipt.v0.1.schema.json`

Purpose: compact public-safe summary of dry-run or execution outcome.

The receipt is a summary, not a raw log. It records fields such as runtime mode, status, return code, reason, execution source, dry-run flag, command input summary, planned/executed command counts, and whether stdout/stderr existed.

Current limitations:

- does not include raw output;
- does not prove the raw private evidence;
- has no identity/signature model.

### EvidenceBundle

Schema: `schemas/evidence_bundle.v0.1.schema.json`

Purpose: summarize public-safe evidence criteria and non-claims for a proof trace.

Current proof mode:

- `dry_run_contract_proof`

Current limitations:

- does not claim live vulnerability evidence;
- does not include forensic evidence storage;
- does not include artifact hashes or private evidence references.

### ScopeFidelityReport

Schema: `schemas/scope_fidelity_report.v0.1.schema.json`

Purpose: static host-binding review for a target and execution shape.

Inputs:

- target URL/host;
- normalized argument scalars;
- execution-plan step objects with `args` and optional `stdin`.

Verdicts:

- `pass`: detected hosts match the target host;
- `review`: no host is detectable from the execution shape;
- `fail`: at least one detected host differs from the target host.

Current limitations:

- static only;
- no DNS resolution;
- no redirect following;
- no file loading;
- no encoded payload decoding beyond simple scalar parsing;
- no ownership/authorization proof.

### SecurityContractValidationReceipt

Schema: `schemas/security_contract_validation_receipt.v0.1.schema.json`

Purpose: record which local/public-safe SCL validation checks ran and whether they passed.

Current package CLI can emit this receipt for fixture validation. The receipt explicitly states:

- `live_target_execution: false`
- `protocol_adapter_work: false`
- `public_push: false`

Current limitations:

- records local validation, not external CI truth;
- does not authorize publication;
- does not sign validation output.

## JSON Schema validation status

The package includes a small dependency-free JSON Schema subset validator in `scl.artifacts`. It supports the subset used by current schemas, including:

- `const`
- `enum`
- `type`
- `minLength`
- `minimum`
- `required`
- `properties`
- `additionalProperties: false`
- array item validation

The schemas declare JSON Schema draft 2020-12, but the built-in validator is not a full draft 2020-12 implementation. If this project grows toward broader third-party schema compatibility, replacing or supplementing the validator with a full JSON Schema implementation is a reasonable next step.

## Versioning notes

v0.1 currently preserves some artifact versions inherited from the reference runtime, for example `2026-03-18.approved.v1` for `ApprovedExecutionSpec` and date-stamped schema versions for policy/evidence artifacts.

This is acceptable for a draft candidate. A future v1 should simplify version naming and define compatibility/version negotiation more explicitly.

## Security and safety model

SCL v0.1 improves reviewability; it does not by itself create safety. A safe system using SCL still needs:

- real scope policy;
- tool allowlists;
- approval authority;
- executor isolation;
- private evidence storage;
- secret scanning/redaction beyond generic helpers;
- audit logging;
- publication review.

## Non-claims

- SCL does not execute tools.
- SCL does not prove legal authorization.
- SCL does not prove live vulnerabilities.
- SCL is not tamper-proof; v0.1 has no signatures or hash-chain.
- SCL is not a runtime sandbox.
- SCL is not a policy engine by itself.
- SCL is carrier-neutral payload/schema/validation infrastructure, not an OpenClaw/MCP/A2A replacement.
