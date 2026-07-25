# SCLite Artifacts

Current package: `sclite-core==2.0.0`; latest published public package:
`sclite-core==2.0.0`.

The current integration front door is the review lifecycle: canonical artifact
descriptors, lifecycle manifests, scoped tickets, receipt-bounded evidence,
review records, review bundles and explicit verification results.

Artifact schema versions are contract identifiers, not package release numbers.
For example, `review_record.v0.1` remains a current schema in SCLite 2.0.

## Canonical lifecycle

```text
intent_contract
  -> policy_decision
  -> execution_contract
  -> execution_ticket
  -> execution_receipt
  -> evidence_contract
  -> artifact_chain_manifest
```

| Artifact | Current schema | What it records |
| --- | --- | --- |
| Intent contract | `intent_contract.v0.2` | Requested intent before governance or execution authority exists |
| Policy decision | `policy_decision.v0.2`, `policy_decision.v0.3` | An external governance result bound to intent; SCLite validates shape and binding |
| Execution contract | `execution_contract.v0.2`, `execution_contract.v0.3` | Exact bounded execution shape prepared by a host |
| Execution ticket | `execution_ticket.v0.2`, `execution_ticket.v0.3` | Approval/reference and scope bounds for an exact execution contract |
| Execution receipt | `execution_receipt.v0.2` | What an external runtime reports it executed, blocked or dry-ran |
| Evidence contract | `evidence_contract.v0.2` | Receipt-bounded claims, non-claims and evidence references |
| Chain manifest | `artifact_chain_manifest.v0.2` | Ordered canonical descriptors and hash links over lifecycle artifacts |

SCLite validates and verifies these records. GovEngine owns governance and
admission. RExecOp owns execution and runtime lifecycle. A profile owns domain
meaning. Artifact presence does not prove authorization, signer identity,
runtime enforcement or truth of raw evidence.

## Review and verification artifacts

| Artifact | Current schema | Boundary |
| --- | --- | --- |
| Review record | `review_record.v0.1` | Deterministic local review summary with checks, verdict and non-claims |
| Scope Fidelity report | `scope_fidelity_report.v0.1`, `scope_fidelity_report.v0.2` | Static comparison of declared target/scope fields; not a network scope authority |
| Verification result | `verification_result.v1`, `verification_result.v1.1` | Structured status of checks actually performed |
| Kernel Guard manifest | `kernel_guard_hmac_v1` | Shared-secret authentication over a manifest transcript; not PKI or replay protection |

`verification_result` values are structured outcomes, not authority tokens.
Replay, public identity and runtime enforcement remain explicit
`not_checked`/external-owner layers unless a host performs those checks.

## Trust and carrier references

| Artifact | Current schemas | Boundary |
| --- | --- | --- |
| Trust profile reference | `trust_profile_ref.v0.1`, `trust_profile_ref.v0.2` | Digest-bound opaque trust/verifier reference |
| Carrier profile reference | `carrier_profile_ref.v0.1`, `carrier_profile_ref.v0.2` | Digest-bound opaque transport/carrier reference |

SCLite checks shape, identifier rules and digest binding. It does not verify a
signature, decide trust, contact a transparency log, deliver a carrier payload
or operate a revocation service.

## Publication-hygiene artifacts

| Artifact | Current schemas | Boundary |
| --- | --- | --- |
| Redaction policy | `redaction_policy.v0.1`, `redaction_policy.v0.2` | Records configured redaction checks; does not prove secret absence |
| Redaction receipt | `redaction_receipt.v0.1`, `redaction_receipt.v0.2` | Binds source/redacted descriptors and performed checks |
| Validation surface index | `public_validation_surface_index.v0.1`, `public_validation_surface_index.v0.2` | Inventory of selected validation surfaces |
| Snapshot manifest | `public_snapshot_manifest.v0.1`, `public_snapshot_manifest.v0.2` | Descriptor inventory over selected files |

The v0.2 disclosure model is monotonic:

```text
unknown -> operator_asserted -> checks_performed -> externally_verified
```

No disclosure status grants publication authority and SCLite 2.0 does not emit
a derived `public_safe` boolean.

## Review bundle

A canonical review bundle contains:

```text
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

`sclite review` validates and reviews a local bundle.
`sclite export-review-bundle` uses fail-closed `public_export` inventory rules
by default. See [`REVIEW_BUNDLES.md`](REVIEW_BUNDLES.md).

## Removed 1.x orchestration surfaces

Reaction, trigger, watchdog and automation modules, schemas and root exports
were removed in SCLite 2.0. RExecOp owns those mechanics and their historical
artifact resolver. They are not current SCLite artifact families.

The superseded proof-trace product path is also retired and absent from the
installed package. Migration details live in
[`MIGRATING_TO_2.md`](MIGRATING_TO_2.md); historical package evolution belongs
in [`../CHANGELOG.md`](../CHANGELOG.md) and
[`archive/ROADMAP_VERSION_HISTORY.md`](archive/ROADMAP_VERSION_HISTORY.md).

## Validation

Use kernel commands for contract and verification operations:

```bash
sclite validate-artifact --schema intent_contract.v0.2 path/to/intent.json
sclite validate-chain path/to/artifact_chain_manifest.json
sclite verify-lifecycle path/to/artifact_chain_manifest.json
sclite verify-ticket-use path/to/execution_ticket.json \
  --contract path/to/execution_contract.json \
  --receipt path/to/execution_receipt.json \
  --evidence-contract path/to/evidence_contract.json
sclite review path/to/review-bundle --format json
```

Inspection and fixture helpers such as `hash-artifact`, `scope-fidelity`,
`review-lifecycle` and `explain-ticket` use `sclite-devtools`.

Schema compatibility rules are documented in
[`SCHEMA_COMPATIBILITY.md`](SCHEMA_COMPATIBILITY.md). The complete top-level
Python API is documented in [`PUBLIC_API.md`](PUBLIC_API.md).
