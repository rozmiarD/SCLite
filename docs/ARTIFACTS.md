# SCL Artifact Guide

This guide explains the v0.1 artifacts in practical reviewer language. It mirrors the current schemas and helpers in this repository; it does not describe features that are not implemented here.

## Quick map

| Artifact | File in example | Schema-backed? | Built/validated by this package? |
| --- | --- | --- | --- |
| `PolicyDecision` | `examples/security-contract-proof/policy_decision.json` | Yes | Validated |
| Redacted prepared spec | `examples/security-contract-proof/prepared_execution_spec.redacted.json` | No dedicated schema yet | Loaded as fixture |
| `ApprovedExecutionSpec` | `examples/security-contract-proof/approved_execution_spec.json` | Yes | Validated |
| `ExecutionReceipt` | `examples/security-contract-proof/execution_receipt.json` | Yes | Built/validated |
| `EvidenceBundle` | `examples/security-contract-proof/evidence_bundle.json` | Yes | Built/validated |
| Evidence summary | `examples/security-contract-proof/evidence_summary.md` | Markdown, no schema | Loaded as fixture |
| `ScopeFidelityReport` | `examples/scope-fidelity-report/scope_fidelity_report.json` | Yes | Built/validated |
| `SecurityContractValidationReceipt` | CLI output | Yes | Built/validated |

## PolicyDecision

A `PolicyDecision` captures the decision state before execution is approved. It is useful when a reviewer wants to know whether a target/tool/action was allowed, denied, or required owner review.

What it can show:

- decision label;
- reason code;
- target/scope facts;
- tool/action facts;
- whether additional approval is required;
- whether redaction is required.

What it cannot show by itself:

- complete legal authorization;
- a full bug bounty scope policy;
- proof that a later runtime respected the decision.

## Redacted prepared spec

The redacted prepared spec is a public/auditor-facing view of a prepared execution shape.

In v0.1 this package treats it as part of the proof fixture, but there is not yet a dedicated schema. That is intentional: runtime-specific prepared specs can include fields this small core should not own yet.

Useful future work: define `prepared_execution_spec.v0.1` and `redacted_prepared_execution_spec.v0.1` once the neutral field set is clearer.

## ApprovedExecutionSpec

An `ApprovedExecutionSpec` is the handoff shape between approval and a governed executor.

It is the artifact that should answer: “what exactly was approved for execution?”

Important review fields:

- target and target host;
- whether the target was considered in scope by the producer;
- resolved tool;
- normalized args;
- execution plan;
- approval object;
- execution truth object.

This package validates the shape. It does not run the spec.

## ExecutionReceipt

An `ExecutionReceipt` is a compact summary of dry-run/execution truth.

It is not a raw log. It intentionally avoids raw private stdout/stderr content. A runtime can keep raw artifacts privately and publish only this compact public-safe summary.

Review it for:

- runtime mode;
- status;
- return code;
- dry-run flag;
- execution source;
- command input summary;
- planned/executed command counts;
- stdout/stderr presence booleans.

## EvidenceBundle

An `EvidenceBundle` summarizes what the proof trace supports and, equally importantly, what it does not claim.

The current fixture uses `dry_run_contract_proof`, meaning it demonstrates contract/proof structure, not live vulnerability finding.

Review it for:

- proof mode;
- criteria;
- non-claims;
- source artifacts;
- public-safety flags.

## ScopeFidelityReport

A `ScopeFidelityReport` is a static host-binding review artifact.

It can answer: “does this execution shape appear to target the same host as the declared target?”

It returns:

- `pass` when detected hosts match;
- `review` when no host can be detected;
- `fail` when a different host appears.

It is deliberately conservative. `review` is not a failure; it means a human/system should inspect a shape where the simple static detector cannot infer host binding.

## SecurityContractValidationReceipt

A `SecurityContractValidationReceipt` records validation checks and their result.

In this package, the CLI emits it for fixture validation. A larger runtime may produce a richer receipt over multiple checks, but the v0.1 schema keeps the public-safe scope explicit:

- no live target execution;
- no protocol adapter work;
- no public push authorization.

## How to review the example fixture

Run:

```bash
python -m sclite.cli validate examples/security-contract-proof
python -m sclite.cli validate-artifact --schema scope_fidelity_report.v0.1 examples/scope-fidelity-report/scope_fidelity_report.json
python -m sclite.cli scope-fidelity --approved-spec examples/security-contract-proof/approved_execution_spec.json --fail-on review
python -m sclite.cli validation-receipt examples/security-contract-proof
```

A passing result means the local synthetic fixture matches the current schemas/invariants. It does not mean the project executed tools or found a vulnerability.
