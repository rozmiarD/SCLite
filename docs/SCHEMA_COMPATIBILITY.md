# SCLite Schema Compatibility Matrix

This matrix separates package release lines from artifact schema versions.
`sclite-core==1.0.4` is the current published package line; most current
artifact contracts intentionally remain on earlier schema versions.

## Current Supported Combinations

| Surface | Current schema | Status | Demonstrated by | Notes |
| --- | --- | --- | --- | --- |
| Intent contract | `intent_contract.v0.2` | current | `sclite/examples/contract-lifecycle-v0.2/`, `examples/govengine-integration/` | Describes requested work only. |
| Policy decision | `policy_decision.v0.2` | current | same lifecycle fixtures | Policy result artifact, not a policy engine. |
| Execution contract | `execution_contract.v0.2` | current | lifecycle and GovEngine fixtures | `execution_shape.plan` is an opaque normalized execution-shape field, not planner ownership or runtime permission. Rename only in a vNext schema. |
| Execution ticket | `execution_ticket.v0.2` | legacy-current for canonical lifecycle | `sclite/examples/contract-lifecycle-v0.2/` | Still validates and remains useful for lifecycle compatibility. |
| Execution ticket | `execution_ticket.v0.3` | current for scoped ticket use | `sclite/examples/scoped-ticket-v0.3/`, `examples/govengine-integration/` | Adds scoped ticket semantics consumed by `validate-ticket`, `explain-ticket`, and `verify-ticket-use`. |
| Execution receipt | `execution_receipt.v0.2` | current | lifecycle, scoped-ticket, and GovEngine fixtures | Public-safe receipt summary; not raw evidence storage. |
| Evidence contract | `evidence_contract.v0.2` | current with compatibility fallback | scoped-ticket and GovEngine fixtures | Structured claim booleans are authoritative; legacy text markers remain conservative fallback for v0.2 fixtures. |
| Artifact chain manifest | `artifact_chain_manifest.v0.2` | current | lifecycle and review fixtures | Security binding comes from descriptors and `root_chain_digest`, not arbitrary IDs. |
| Kernel Guard sidecar | `kernel_guard_hmac_v1.schema.json` | current guarded profile | `tests/golden/kernel_guard_hmac_v1/` | HMAC domain authenticity only; incompatible transcript changes require a new profile name. |
| Verification result | `verification_result.v1` | current secure verifier result | `tests/test_secure_bundle.py`, `tests/test_internal_package.py` | Layer statuses keep replay, public identity, and runtime enforcement as non-claims. |
| Review record | `review_record.v0.1` | current review output | `examples/govengine-integration/verification_receipt.json` | Static public-safe review result. |
| Review bundle shape | `0.5` directory convention | current downstream boundary | `examples/review-bundle/`, `examples/govengine-integration/` | Directory contract, not a separate JSON schema version. |

## Planned Or Not Supported

| Surface | Status | Compatibility decision |
| --- | --- | --- |
| `execution_receipt.vNext` | planned only | Should make outcome taxonomy and evidence claim requirements explicit enough to retire text-marker fallback later. |
| `evidence_contract.vNext` | planned only | Should preserve public-safe review output and structured receipt binding without adding raw evidence storage to SCLite. |
| `kernel_guard_hmac_v2` | not implemented | Required only if transcript layout, canonicalization, HMAC fields, or metadata digest semantics become incompatible. |
| `public_signed_export` | not implemented | Future optional public-root signature surface; current HMAC profile is not PKI or non-repudiation. |
| Runtime replay store | not supported in SCLite | `guarded_domain_auth_fresh` belongs to GovEngine or another host runtime with state. |

## Unknown Fields Policy

Many current schemas preserve forward compatibility by allowing additional
properties. Unknown fields are metadata unless SCLite code explicitly names
and validates them. They do not override known security-critical semantics
such as descriptor digests, lifecycle role order, strict role/schema identity,
ticket approval status,
receipt/evidence links, Kernel Guard transcripts, or verifier result
non-claims.

Hosts must not treat unknown fields as authorization, identity, replay
freshness, or runtime-enforcement authority. Security-critical behavior needs
a named field, documented semantics, schema coverage, and tests before it can
be consumed as authority.

## Artifact IDs And Digests

Artifact IDs are labels unless a descriptor or link binds them to canonical
artifact bytes. High-risk hosts should carry digest-bound identifiers derived
from stable descriptors, for example `role:digest-prefix` in host-local logs,
while continuing to use SCLite descriptors and `root_chain_digest` as the
security binding.

SCLite does not provide a global artifact registry, identity authority, or
public provenance service.

## GovEngine Compatibility

GovEngine compatibility is consumer compatibility, not a core dependency.
SCLite's repo-level smoke is `tests/test_govengine_integration_surface.py` and
the public-safe fixture under `examples/govengine-integration/`. A downstream
checkout may run the same import and CLI surfaces against its own widened
dependency range, but SCLite must not import GovEngine in production code.
