# SCLite Draft Specification

Status: **published 1.0.9 stable: frozen lifecycle/review and guarded verification surface**.
Current package is `sclite-core==1.0.9`, and the Python import package remains
`sclite`. The current front door is the review lifecycle substrate:
v0.2 lifecycle artifacts, v0.3 scoped ticket / receipt-bounded evidence checks,
v0.5 review-bundle packaging, guarded-strict verification, and bounded
truth-layer artifacts for reactions, trigger decisions, and watchdog
decisions. The 1.0 stable release freezes that substrate as the root API and
supports canonical review-bundle materialization for active consumers without
adding runtime, scheduler, event catcher, adapter, PKI, recovery, or policy
authority.

Artifact schema versions and package release lines are different concepts. New
integrations should treat the lifecycle/review-bundle path as current. The
superseded proof-trace product path is retired after Ravenclaw migrated to the
current lifecycle/review-bundle front door.
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

`validate-chain` verifies the ordered hash-chain. `verify-lifecycle` applies
the lifecycle gate on top and fails closed unless the manifest contains exactly
the canonical v0.2 role sequence with no extra roles, duplicate roles, or
changed order.

`verify-guarded-chain` verifies an optional `kernel_guard_hmac_v1` sidecar over
an artifact-chain manifest. The guard is HMAC-SHA256 over canonical JSON
transcripts for each manifest entry plus a root transcript that binds
`root_chain_digest` and manifest metadata. It provides authenticity only inside
the GovEngine/KERNEL domain that knows the secret; replay freshness remains a
GovEngine replay-store responsibility.

`verify-secure-bundle` is the official guarded-strict verification profile for
runtime-consumable bundles. It is fail-closed and always performs artifact
chain verification, exact strict lifecycle verification, Kernel Guard HMAC
verification, and manifest metadata binding. Missing guard material is a
failure, not a warning. SCLite still reports replay freshness as not checked;
GovEngine records freshness for the `guarded_domain_auth_fresh` posture.

The stable verifier-result contract is `verification_result.v1`. Secure-bundle
JSON output nests it under `verification_result` and keeps the layer statuses
explicit:

```json
{
  "artifact_chain": "pass",
  "strict_lifecycle": "pass",
  "kernel_guard": "pass",
  "replay": "not_checked",
  "public_identity": "not_claimed",
  "runtime_enforcement": "not_claimed"
}
```

`verification_result.v1` is a local verification receipt only. It makes
non-claims machine-readable and does not add replay state, public identity,
policy authorization, or runtime enforcement to SCLite.

The stable top-level Python import surface is documented in
[`docs/PUBLIC_API.md`](docs/PUBLIC_API.md). Patch releases may add new names,
but removal or rename of those exports is a compatibility change for the 1.0
line.

Supported schema-version combinations, unknown-field policy, artifact ID
guidance, and GovEngine consumer compatibility are frozen in
[`docs/SCHEMA_COMPATIBILITY.md`](docs/SCHEMA_COMPATIBILITY.md).

Security posture modes are explicit:

- `integrity_only`: SHA-256 artifact-chain consistency.
- `strict_lifecycle`: integrity plus exact lifecycle role semantics.
- `guarded_domain_auth`: strict lifecycle plus HMAC domain authenticity.
- `guarded_domain_auth_fresh`: HMAC domain authenticity plus GovEngine replay
  freshness.
- `public_signed_export`: future Ed25519/root-anchor export mode, not
  implemented here.

The security model is frozen for the 1.0 release line in
[`SECURITY_MODEL.md`](SECURITY_MODEL.md) and
[`docs/SECURITY_PROFILES.md`](docs/SECURITY_PROFILES.md). For
`kernel_guard_hmac_v1`, SCLite canonical JSON settings, per-entry transcript
fields, root transcript fields, `manifest_metadata_digest()` semantics, and
HMAC-SHA256 tag calculation are compatibility-critical. Any incompatible change must use a new profile name.
For example, use `kernel_guard_hmac_v2`; do not silently change
`kernel_guard_hmac_v1`.

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

## Reaction, Trigger, And Watchdog Truth Artifacts

SCLite also provides bounded artifacts for deterministic automation chains.
They record what an external runtime and governance layer decided; they do not
interpret rules, monitor infrastructure, schedule work, recover operations, or
execute commands.

### ObservationEnvelope v0.1

Schema: `schemas/observation_envelope.v0.1.schema.json`

Captures profile-owned facts observed by a runtime for one operation, intent,
and target. Facts remain domain/profile data. SCLite only validates and hashes
the envelope.

### Finding v0.1

Schema: `schemas/finding.v0.1.schema.json`

Captures a profile-owned taxonomy result and summary linked to an observation
descriptor. SCLite verifies the link shape and descriptor binding; it does not
own the taxonomy or decide severity.

### ReactionPlan v0.1

Schema: `schemas/reaction_plan.v0.1.schema.json`

Captures a deterministic reaction decision linked to the observation and
finding descriptors. It records rule digest, bounded context, idempotency key,
depth, visited-rule digests, and GovEngine admission status. RExecOp owns rule
interpretation and child-operation planning; GovEngine owns admission; SCLite
owns the digest-bound record.

### EscalationProposal v0.1

Schema: `schemas/escalation_proposal.v0.1.schema.json`

Captures an explicitly untrusted advisory proposal for a human or external
assistant lane. It must not carry executable commands, secrets, runtime
authority, or policy bypass. Any later operation still needs profile validation
and GovEngine admission.

### TriggerDecision v0.1

Schema: `schemas/trigger_decision.v0.1.schema.json`

Captures a bounded event/trigger decision made by RExecOp after GovEngine
admission. It records event, rule-set, rule, admission, and optional child
operation references. Matching events, dedupe/cooldown state, scheduling and
child-operation creation remain outside SCLite.

### WatchdogDecision v0.1

Schema: `schemas/watchdog_decision.v0.1.schema.json`

Captures a bounded runner-watchdog decision made by RExecOp after GovEngine
admission. It records watchdog observation, admission, affected
operation/event/inbox references, and optional manual-recovery context for
GovEngine-admitted recovery or break-glass records. Worker supervision,
runtime recovery, infrastructure health interpretation and retry execution
remain outside SCLite.

## v0.2 Integrity Chain

SCLite v0.2 separates structural chain integrity from strict lifecycle
semantics. `validate-chain` verifies:

1. every manifest entry path stays within the selected artifact root;
2. every artifact descriptor matches the canonical SHA-256 digest of the local JSON artifact;
3. every `previous_chain_digest` and `chain_digest` is recomputed in order;
4. the `root_chain_digest` matches the final recomputed chain digest.

`verify-lifecycle` and `validate-chain --strict-lifecycle` additionally verify:

5. the exact canonical lifecycle role sequence for
   v0.2 lifecycle manifests, with no extra or duplicate roles;
6. `policy_decision` binds the correct `intent_contract` digest;
7. `execution_contract` binds the correct intent and policy decision digests;
8. `execution_ticket` binds the correct `execution_contract` descriptor and `integrity.ticket_binds_execution_contract_digest`;
9. denied policy decisions do not continue into an executable lifecycle;
10. owner-approval-required policy decisions require a consumable approved ticket before executable lifecycle review can pass;
11. rejected, expired, revoked, missing, or unknown ticket approval states stop executable lifecycle review;
12. `execution_receipt` binds the correct `execution_ticket` and `execution_contract` digests;
13. `evidence_contract` binds the correct `execution_receipt` and `execution_ticket` digests.

Python callers can use `verify_lifecycle_manifest()` as the fail-safe wrapper
for this strict behavior instead of remembering to pass `require_lifecycle=True`
to `verify_artifact_chain_manifest()`.

## Optional Kernel Guard HMAC

`kernel_guard_hmac_v1` is an optional sidecar profile. It does not change the
artifact body digest model and does not make SCLite a key store, PKI verifier,
runtime, or replay authority.

Per-entry transcripts bind:

- profile, chain id, sequence, entry count;
- entry role and path;
- descriptor digest, artifact type, schema ref, schema version,
  canonicalization, and hash algorithm;
- previous HMAC tag, nonce, and key id.

The root transcript binds:

- profile and chain id;
- entry count;
- first and last entry tag;
- `root_chain_digest`;
- manifest metadata digest;
- key id.

This is lightweight cryptographic integrity, not identity trust. It proves the verifier saw the same canonical artifact bytes and lifecycle links; it does not prove who created them, whether a human was legally authorized, or whether a runtime enforced them.

## v0.3 Scoped Ticket Use

The `0.3.5` line includes the first scoped-ticket and receipt-bounded-evidence surfaces:

- `execution_ticket.v0.3` for runtime-consumable scoped-ticket artifacts;
- `sclite validate-ticket` and `sclite explain-ticket` for ticket review;
- `sclite verify-ticket-use` for static receipt/evidence checks against a scoped ticket, including explicit receipt-source binding and conservative completed-execution/network claim bounds.

These checks remain local artifact verification. They do not execute tools, decide authorization, prove signer identity, or attest that a runtime enforced a ticket.

Receipt/evidence compatibility decision:

- structured claim booleans such as `requires_completed_execution`,
  `requires_network_execution`, and `requires_live_execution` are authoritative
  for current receipt-bounded evidence review;
- legacy text markers such as `completed_execution`, `command_executed`, and
  `network_execution` remain a conservative compatibility fallback in v0.2 so
  old public-safe fixtures cannot bypass receipt bounds by omitting structured
  fields;
- an execution receipt vNext should make outcome taxonomy and evidence claim
  requirements explicit enough that text marker fallback can be deprecated in a
  future schema line;
- `execution_shape.plan` remains an opaque normalized execution-shape field in
  v0.2. It is not planner ownership or runtime permission. Any rename should
  happen only in a vNext schema.

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

## Retired proof-trace product path

SCLite used the following public-safe proof trace as migration input during
early alpha development:

```text
scope/input -> policy decision -> prepared execution spec -> approved execution spec -> dry-run execution receipt -> evidence summary
```

The legacy builders, fixture validators, schemas owned only by this trace, and
its fixture directories are not part of the `1.0.0` installed/current
surface. Current work uses the lifecycle/review-bundle model above. Generic
redaction, snapshot-manifest, Scope Fidelity, and review-record schemas remain
because the current lifecycle still uses them; their schema suffixes are
format identifiers, not legacy product support.

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
define / validate / hash / bind / redact / review / verify
```

Runtimes such as Ravenclaw may consume SCLite artifacts, enforce tickets, execute or dry-run tools, store raw evidence, and expose carrier adapters. Those responsibilities stay outside SCLite.

## Roadmap Boundary

Future SCLite work is expected to keep this split intact. Post-0.5 work should improve examples, failure drills, optional verifier integrations, and runtime handoff clarity while keeping policy decisions, trust decisions, live execution, revocation, raw evidence storage, and carrier adapter implementation outside SCLite core. See [`ROADMAP.md`](ROADMAP.md) for the versioned roadmap.
