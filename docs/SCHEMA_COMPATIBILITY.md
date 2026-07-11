# SCLite Schema Compatibility Matrix

This matrix separates package release lines from artifact schema versions.
`sclite-core==2.0.0` is the current published stable release; most current
artifact contracts intentionally remain on earlier schema versions.

## Current Supported Combinations

| Surface | Current schema | Status | Demonstrated by | Notes |
| --- | --- | --- | --- | --- |
| Intent contract | `intent_contract.v0.2` | current | `sclite/examples/contract-lifecycle-v0.2/`, `examples/govengine-integration/` | Describes requested work only. |
| Policy decision | `policy_decision.v0.2` | supported legacy | same lifecycle fixtures | Legacy boolean scope assertion; no authority provenance. |
| Policy decision | `policy_decision.v0.3` | current additive | RExecOp/GovEngine provenance vectors | Embeds a digest-bound GovEngine scope-decision artifact without authenticating the authority string. |
| Execution contract | `execution_contract.v0.2` | supported legacy | lifecycle and GovEngine fixtures | Legacy `target_in_scope` compatibility field. |
| Execution contract | `execution_contract.v0.3` | current additive | lifecycle and GovEngine fixtures | Copies the exact scope assertion and binds it to execution target identity. |
| Execution ticket | `execution_ticket.v0.2` | legacy-current for canonical lifecycle | `sclite/examples/contract-lifecycle-v0.2/` | Still validates and remains useful for lifecycle compatibility. |
| Execution ticket | `execution_ticket.v0.3` | current for scoped ticket use | `sclite/examples/scoped-ticket-v0.3/`, `examples/govengine-integration/` | Adds scoped ticket semantics consumed by `validate-ticket`, `explain-ticket`, and `verify-ticket-use`. |
| Execution receipt | `execution_receipt.v0.2` | current | lifecycle, scoped-ticket, and GovEngine fixtures | Public-safe receipt summary; not raw evidence storage. |
| Evidence contract | `evidence_contract.v0.2` | current with compatibility fallback | scoped-ticket and GovEngine fixtures | Structured claim booleans are authoritative; legacy text markers remain conservative fallback for v0.2 fixtures. |
| Observation envelope | `observation_envelope.v0.1` | current | `tests/test_reactions.py` | Profile/runtime facts projection; SCLite does not own domain facts. |
| Finding | `finding.v0.1` | current | `tests/test_reactions.py` | Profile-owned taxonomy/severity projection linked to an observation descriptor. |
| Reaction plan | `reaction_plan.v0.1` | current | `tests/test_reactions.py` | Deterministic reaction decision record with depth, idempotency and admission fields; RExecOp/GovEngine own planning and policy. |
| Escalation proposal | `escalation_proposal.v0.1` | current | `tests/test_reactions.py` | Explicitly untrusted advisory artifact; no execution authority or secrets. |
| Trigger decision | `trigger_decision.v0.1` | current | `tests/test_trigger_decisions.py` | Bounded event/rule/GovEngine-admission truth projection; trigger planning remains outside SCLite. |
| Watchdog decision | `watchdog_decision.v0.1` | current | `tests/test_watchdog_decisions.py` | Bounded RExecOp runtime-supervisor observation/admission truth projection with optional manual-recovery context; runtime supervision and recovery remain outside SCLite. |
| Automation chain | `automation_chain.v0.1` | current contract-design baseline | `tests/test_automation_chain.py` | Bounded multi-step automation graph with depth/reaction budgets, edge idempotency, GovEngine admission refs, recovery policy and LLM proposal-only invariants; traversal/execution remains outside SCLite. |
| Artifact chain manifest | `artifact_chain_manifest.v0.2` | current | lifecycle and review fixtures | Security binding comes from descriptors and `root_chain_digest`, not arbitrary IDs. |
| Kernel Guard sidecar | `kernel_guard_hmac_v1.schema.json` | current guarded profile | `tests/golden/kernel_guard_hmac_v1/` | HMAC domain authenticity only; incompatible transcript changes require a new profile name. |
| Verification result | `verification_result.v1` | current secure verifier result | `tests/test_secure_bundle.py`, `tests/test_internal_package.py` | Layer statuses keep replay, public identity, and runtime enforcement as non-claims. |
| Typed verification result | `verification_result.v1.1` | additive typed verifier serialization | `tests/test_typed_verification_result.py`, `tests/test_secure_bundle.py` | Adds bundle digest, policy, verifier version and performed checks; type/schema shape is not authentication. |
| Disclosure/redaction artifacts | `redaction_policy.v0.2`, `redaction_receipt.v0.2`, `public_validation_surface_index.v0.2`, `public_snapshot_manifest.v0.2` | current evidence-based disclosure model | `tests/test_disclosure_status.py`, `tests/test_internal_package.py` | Defaults unknown, records checks/policy/coverage, keeps publication authorization separate and preserves v0.1 schemas unchanged. |
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
