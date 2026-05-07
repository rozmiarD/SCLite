# SCL Artifact Guide

This guide explains the implemented SCLite artifacts in practical reviewer language. v0.2 adds a contract lifecycle model and a lightweight cryptographic integrity chain; v0.1 proof-trace artifacts remain supported.

## v0.2 lifecycle map

| Artifact | File in example | Schema-backed? | Built/validated by this package? |
| --- | --- | --- | --- |
| `IntentContract` | `examples/contract-lifecycle-v0.2/intent_contract.json` | Yes | Validated |
| `PolicyDecision` v0.2 | `examples/contract-lifecycle-v0.2/policy_decision.json` | Yes | Validated |
| `ExecutionContract` | `examples/contract-lifecycle-v0.2/execution_contract.json` | Yes | Validated |
| `ExecutionTicket` | `examples/contract-lifecycle-v0.2/execution_ticket.json` | Yes | Validated; integrity-bound |
| `ExecutionReceipt` v0.2 | `examples/contract-lifecycle-v0.2/execution_receipt.json` | Yes | Validated |
| `EvidenceContract` | `examples/contract-lifecycle-v0.2/evidence_contract.json` | Yes | Validated |
| `ArtifactChainManifest` | `examples/contract-lifecycle-v0.2/artifact_chain_manifest.json` | Yes | Verified by `sclite validate-chain` / `sclite verify-lifecycle` |

The v0.2 integrity model is deliberately lightweight: canonical SHA-256 descriptors plus an ordered hash-linked chain. The verifier also checks lifecycle semantics: canonical role order, policy->intent binding, execution contract->intent/policy binding, ticket->execution contract binding, receipt->ticket binding, evidence->receipt binding, and manifest path containment. It detects local bundle tampering and lifecycle-link drift, but it does not prove signer identity, legal authorization, runtime enforcement, or transparency-log inclusion.

## v0.1 quick map

| Artifact | File in example | Schema-backed? | Built/validated by this package? |
| --- | --- | --- | --- |
| `PolicyDecision` | `examples/security-contract-proof/policy_decision.json` | Yes | Validated |
| `PreparedExecutionSpec` | `examples/prepared-execution-spec/prepared_execution_spec.json` | Yes | Validated |
| `RedactedPreparedExecutionSpec` | `examples/security-contract-proof/prepared_execution_spec.redacted.json` | Yes | Validated |
| `ApprovedExecutionSpec` | `examples/security-contract-proof/approved_execution_spec.json` | Yes | Validated |
| `ExecutionReceipt` | `examples/security-contract-proof/execution_receipt.json` | Yes | Built/validated |
| `EvidenceBundle` | `examples/security-contract-proof/evidence_bundle.json` | Yes | Built/validated |
| Evidence summary | `examples/security-contract-proof/evidence_summary.md` | Markdown, no schema | Loaded as fixture |
| Artifact hash descriptor | Any JSON artifact | No schema in v0.1 | Built by helper/CLI |
| `RedactionPolicy` | `examples/redaction-policy/redaction_policy.json` | Yes | Built/validated |
| `RedactionReceipt` | `examples/redaction-receipt/redaction_receipt.json` | Yes | Built/validated |
| `PublicValidationSurfaceIndex` | `examples/public-validation-surface-index/public_validation_surface_index.json` | Yes | Built/validated |
| `PublicSnapshotManifest` | `examples/public-snapshot-manifest/public_snapshot_manifest.json` | Yes | Built/validated |
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

## PreparedExecutionSpec

A `PreparedExecutionSpec` captures the concrete execution shape before approval. It is useful when a reviewer wants to inspect the target, resolved tool, normalized arguments, execution plan, and static host-binding summaries before an approval artifact exists.

What it can show:

- declared target and target host;
- whether the producer considered the target in scope;
- resolved tool and normalized args;
- execution-plan steps;
- scope facts and request-shape hygiene summaries.

What it cannot show by itself:

- approval authority;
- live execution truth;
- legal authorization;
- cryptographic binding to a policy decision.

## RedactedPreparedExecutionSpec

A `RedactedPreparedExecutionSpec` is a public/auditor-safe view of a prepared execution shape. It validates the same reviewable target/tool/plan core and also requires explicit redaction/public-safety flags.

It should not include raw stdout/stderr, credentials, private paths, or live target evidence. The schema requires public-safety booleans to remain false for those claims, but a runtime still needs real upstream redaction and secret scanning.

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


## Artifact hash descriptor

SCLite can emit a deterministic SHA-256 descriptor for any JSON-compatible artifact:

```bash
sclite hash-artifact --schema approved_execution_spec.v0.1 examples/security-contract-proof/approved_execution_spec.json
```

The helper canonicalizes JSON with sorted keys, compact separators, preserved Unicode, and UTF-8 bytes, then hashes those bytes with SHA-256. The descriptor is useful for content addressing, fixture comparison, and lightweight reviewer references.

It is not a signature, identity proof, authorization proof, or tamper-proof audit chain. A runtime that needs provenance must add signing/identity controls outside this helper.


## RedactionPolicy and RedactionReceipt

`RedactionPolicy` documents public-safe redaction rules. `RedactionReceipt` records a redaction operation using policy/source/redacted hashes and summary counts while excluding raw source material.

They are useful for reviewer traceability, but they are not a complete secret scanner, not proof that upstream data never contained secrets, and not publication authorization.

## PublicValidationSurfaceIndex and PublicSnapshotManifest

`PublicValidationSurfaceIndex` lists public-safe validation surfaces and commands. `PublicSnapshotManifest` describes selected public-safe files and can include SCLite canonical hash descriptors.

These artifacts help reviewers understand what can be validated locally. They do not claim live execution, protocol adapter coverage, signed provenance, or push/package publication authorization.

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
python -m sclite.cli validate-chain sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json
python -m sclite.cli verify-lifecycle sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json
python -m sclite.cli validate examples/security-contract-proof
python -m sclite.cli validate-artifact --schema prepared_execution_spec.v0.1 examples/prepared-execution-spec/prepared_execution_spec.json
python -m sclite.cli validate-artifact --schema redacted_prepared_execution_spec.v0.1 examples/security-contract-proof/prepared_execution_spec.redacted.json
python -m sclite.cli validate-artifact --schema scope_fidelity_report.v0.1 examples/scope-fidelity-report/scope_fidelity_report.json
python -m sclite.cli hash-artifact --schema approved_execution_spec.v0.1 examples/security-contract-proof/approved_execution_spec.json
python -m sclite.cli validate-artifact --schema redaction_policy.v0.1 examples/redaction-policy/redaction_policy.json
python -m sclite.cli validate-artifact --schema redaction_receipt.v0.1 examples/redaction-receipt/redaction_receipt.json
python -m sclite.cli validate-artifact --schema public_validation_surface_index.v0.1 examples/public-validation-surface-index/public_validation_surface_index.json
python -m sclite.cli validate-artifact --schema public_snapshot_manifest.v0.1 examples/public-snapshot-manifest/public_snapshot_manifest.json
python -m sclite.cli scope-fidelity --approved-spec examples/security-contract-proof/approved_execution_spec.json --fail-on review
python -m sclite.cli validation-receipt examples/security-contract-proof
```

A passing result means the local synthetic fixture matches the current schemas/invariants. It does not mean the project executed tools or found a vulnerability.
