# SCL Artifact Guide

This guide explains the implemented SCLite artifacts in practical reviewer
language.

Current public package line: `sclite-core==0.7.0a0`
(`0.7.0-alpha`). The current integration front door is the review lifecycle
substrate: v0.2 lifecycle artifacts, v0.3 scoped ticket /
receipt-bounded-evidence checks, and v0.5 review-bundle packaging. Package
release labels and artifact schema versions are separate concepts.

Legacy v0.1 artifacts are compatibility/history material for Ravenclaw
public-proof migration, not the current front door for new integrations. The
The `0.7.0-alpha` line implements Ravenclaw-first surface collapse: v0.1 is not
part of the active root API, while explicit compatibility modules remain for
historical fixtures and migration validation.

## Lifecycle map

```mermaid
flowchart LR
    Intent[intent_contract] --> Policy[policy_decision]
    Policy --> Contract[execution_contract]
    Contract --> Ticket[execution_ticket]
    Ticket --> Receipt[execution_receipt]
    Receipt --> Evidence[evidence_contract]
    Evidence --> Manifest[artifact_chain_manifest]
```

## Current review-bundle surface

SCLite's current review-bundle surface packages the six lifecycle artifacts, an
artifact-chain manifest, reviewer Markdown, and a verification receipt into one
local/public-safe directory. The 0.6 alpha package line preserves the 0.5
review-bundle contract and adds public-truth and multi-fixture hardening around
it.

The fixture at `examples/review-bundle/` demonstrates the base shape and can be reviewed with:

```bash
python -m sclite.cli review examples/review-bundle --format json
python -m sclite.cli review examples/review-bundle --format summary
python -m sclite.cli export-review-bundle examples/review-bundle --format markdown
```

The bundled base fixture returns `review`, not `pass`, because it intentionally demonstrates the v0.2 lifecycle ticket rather than newer scoped `execution_ticket.v0.3` ticket-use semantics. That conservative verdict is part of the point: SCLite should make reviewer attention visible instead of overstating what a bundle proves.

The GovEngine integration fixture is expected to pass because it uses the v0.3 scoped-ticket / receipt-bounded-evidence surface and digest-bound profile sidecars:

```bash
python -m sclite.cli review examples/govengine-integration --format json --fail-on review
python -m sclite.cli validate-trust-profile examples/govengine-integration/trust_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json
python -m sclite.cli validate-carrier-profile examples/govengine-integration/carrier_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json
```

`examples/bad-review-bundle-cross-host/` intentionally fails review due to cross-role target drift and is used for negative integration tests.

## v0.3 scoped ticket surface

SCLite 0.3.5 publishes the first `ExecutionTicket` scoped-ticket surface while preserving SCLite's non-authority boundary. A scoped ticket can describe the runtime, target, tool, mode, normalized-argument digest, spend limits, and receipt/evidence obligations that an external runtime should enforce.

The fixture at `sclite/examples/scoped-ticket-v0.3/` demonstrates the shape and can be reviewed with:

```bash
python -m sclite.cli validate-ticket sclite/examples/scoped-ticket-v0.3/execution_ticket.json --contract sclite/examples/scoped-ticket-v0.3/execution_contract.json
python -m sclite.cli explain-ticket sclite/examples/scoped-ticket-v0.3/execution_ticket.json
```

This remains local/static validation. It does not prove legal authorization, signer identity, runtime enforcement, or live vulnerability evidence.

The 0.3.5 Receipt-Bounded Evidence slice adds `verify-ticket-use` for the same fixture:

```bash
python -m sclite.cli verify-ticket-use sclite/examples/scoped-ticket-v0.3/execution_ticket.json --contract sclite/examples/scoped-ticket-v0.3/execution_contract.json --receipt sclite/examples/scoped-ticket-v0.3/execution_receipt.json --evidence-contract sclite/examples/scoped-ticket-v0.3/evidence_contract.json
```

That verifier checks only local accountability bindings: receipt-to-ticket, receipt-to-contract, runtime/mode/network/use limits, evidence-to-receipt, evidence-to-ticket, explicit `source_receipt_id`, receipt-bounded claim flags, completed-execution/network claim bounds, and replay limits.

## v0.4 trust/carrier references and review records

SCLite includes digest-bound trust and carrier reference sidecars:

```bash
python -m sclite.cli validate-trust-profile \
  sclite/examples/trust-carrier-profiles/trust_profile_ref.json \
  --subject sclite/examples/scoped-ticket-v0.3/execution_ticket.json
python -m sclite.cli validate-carrier-profile \
  sclite/examples/trust-carrier-profiles/carrier_profile_ref.json \
  --subject sclite/examples/scoped-ticket-v0.3/execution_ticket.json
```

These checks validate sidecar shape and subject digest binding only. They do not prove signer identity, revocation state, delivery, adapter correctness, or authorization.

Lifecycle review records aggregate static lifecycle checks:

```bash
python -m sclite.cli review-lifecycle \
  sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json \
  --format json
```

The output is a `review_record.v0.1` with conservative `pass` / `review` / `fail` verdicts. Review records are also used as review-bundle verification receipts.

## v0.2 lifecycle map

| Artifact | File in example | Schema-backed? | Built/validated by this package? |
| --- | --- | --- | --- |
| `IntentContract` | `sclite/examples/contract-lifecycle-v0.2/intent_contract.json` | Yes | Validated |
| `PolicyDecision` v0.2 | `sclite/examples/contract-lifecycle-v0.2/policy_decision.json` | Yes | Validated |
| `ExecutionContract` | `sclite/examples/contract-lifecycle-v0.2/execution_contract.json` | Yes | Validated |
| `ExecutionTicket` | `sclite/examples/contract-lifecycle-v0.2/execution_ticket.json` | Yes | Validated; integrity-bound |
| `ExecutionReceipt` v0.2 | `sclite/examples/contract-lifecycle-v0.2/execution_receipt.json` | Yes | Validated |
| `EvidenceContract` | `sclite/examples/contract-lifecycle-v0.2/evidence_contract.json` | Yes | Validated |
| `ArtifactChainManifest` | `sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json` | Yes | Verified by `sclite validate-chain` / `sclite verify-lifecycle` |

The v0.2 integrity model is deliberately lightweight: canonical SHA-256 descriptors plus an ordered hash-linked chain. The verifier also checks lifecycle semantics: canonical role order, policy->intent binding, execution contract->intent/policy binding, ticket->execution contract binding, receipt->ticket/contract binding, evidence->receipt/ticket binding, and manifest path containment. It detects local bundle tampering and lifecycle-link drift, but it does not prove signer identity, legal authorization, runtime enforcement, or transparency-log inclusion.

## Legacy v0.1 quick map

These artifacts remain available for Ravenclaw/public-proof migration and
historical validation. They should not be used as the current SCLite
integration front door for new work.

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

The redaction helpers are blacklist-oriented public-safe fixture helpers. Treat them as part of publication hygiene, not as DLP or a general-purpose secret scanner.

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
python -m sclite.cli review examples/review-bundle --format json
python -m sclite.cli export-review-bundle examples/review-bundle --format markdown
python -m sclite.cli review-lifecycle sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json --format json
python -m sclite.cli validate-trust-profile sclite/examples/trust-carrier-profiles/trust_profile_ref.json --subject sclite/examples/scoped-ticket-v0.3/execution_ticket.json
python -m sclite.cli validate-carrier-profile sclite/examples/trust-carrier-profiles/carrier_profile_ref.json --subject sclite/examples/scoped-ticket-v0.3/execution_ticket.json
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
