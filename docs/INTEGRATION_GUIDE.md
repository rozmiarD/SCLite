# SCLite Integration Guide

The current 2.0 stable release is an offline contract, integrity, review and
verification kernel. Integrate it as a library or CLI verifier; do not use it
as a runtime, policy engine, trust authority or evidence store.

## Stack boundary

```text
Profile intent/workflow
        |
        v
RExecOp lifecycle -----> GovEngine governance/admission
        |
        v
RExecOp execution and runtime facts
        |
        v
SCLite canonical artifacts, integrity, review and verification
```

- A profile owns domain vocabulary, intent catalogs, workflow definitions and
  domain validation.
- GovEngine evaluates policy, approval, scope, capability and admission.
- RExecOp owns lifecycle state, scheduling, retries, connectors and execution.
- SCLite owns canonical artifact contracts, digest binding, lifecycle/evidence
  integrity, review bundles and verification records.

No component acquires another component's authority by serializing its output
into an SCLite artifact.

## Choose the front door

For new Python integrations prefer:

```python
from sclite import VerificationPolicy, verify_artifact, verify_bundle
```

`verify_artifact()` validates one artifact through a packaged or explicitly
provided immutable resolver. `verify_bundle()` requires an explicit
`VerificationPolicy`; it never infers a security posture from input.

Use lower-level modules only when the packaged
`contracts/consumer_imports.v1.json` inventory records the controlled consumer
or when the caller accepts that the import is not a reviewed compatibility
surface.

## Artifact lifecycle

A host may project its already-owned decisions and runtime facts into the
canonical lifecycle:

```text
intent -> policy decision -> execution contract -> ticket
       -> receipt -> evidence contract -> chain manifest
```

The host must retain the original ownership:

- GovEngine produces or authenticates the governance/admission decision;
- RExecOp produces execution/runtime facts and receipts;
- SCLite validates artifact shape, digest links and the selected verification
  profile.

SCLite does not independently establish policy authority, human approval,
runtime identity, execution freshness or raw-evidence truth.

## CLI integration

Kernel commands:

```bash
sclite validate-artifact --schema intent_contract.v0.2 artifact.json
sclite validate-chain artifact_chain_manifest.json
sclite verify-lifecycle artifact_chain_manifest.json
sclite verify-secure-bundle review_bundle --guard kernel_guard_manifest.json
sclite validate-ticket execution_ticket.json --contract execution_contract.json
sclite verify-ticket-use execution_ticket.json \
  --contract execution_contract.json \
  --receipt execution_receipt.json \
  --evidence-contract evidence_contract.json
sclite review review_bundle --format json --fail-on review
sclite export-review-bundle review_bundle --format markdown
```

Devtools commands:

```bash
sclite-devtools hash-artifact artifact.json
sclite-devtools explain-ticket execution_ticket.json
sclite-devtools scope-fidelity --approved-spec approved.json
sclite-devtools review-lifecycle artifact_chain_manifest.json --format json
```

Kernel entrypoints are `sclite` and `scl`. Inspection, fixture and heuristic
redaction commands belong to `sclite-devtools`; the entrypoints intentionally
reject commands owned by the other surface.

See [`CLI_EXIT_CODES.md`](CLI_EXIT_CODES.md) for stable exit semantics.

## Verification posture

Choose posture explicitly:

| Posture | Checks |
| --- | --- |
| `integrity_only` | canonical descriptors and artifact-chain links |
| `strict_lifecycle` | integrity plus exact lifecycle order and semantic bindings |
| `guarded_domain_auth` | manifest integrity plus Kernel Guard shared-secret authentication |
| `guarded-strict` | strict lifecycle plus required Kernel Guard authentication |
| host-owned freshness | an external atomic replay claim layered on a passed guarded result |

For Python callers, lifecycle semantics are enabled by an explicit policy or
`require_lifecycle=True` on the relevant lower-level verifier. Generic chain
verification intentionally remains integrity-only.

Kernel Guard does not provide public identity, non-repudiation, replay
prevention or proof of runtime behavior. A host must atomically claim freshness
and bind the accepted result to its own admission/execution attempt.

## Immutable extension schemas

Domain contracts can be supplied through `ImmutableSchemaResolver`.

Requirements:

- identifiers use `namespace/name@vN`;
- schemas are loaded offline from a reviewed inventory;
- duplicate identifiers and digest collisions fail closed;
- no plugin discovery, network download or process-global registration occurs;
- canonical SCLite schemas keep their packaged identities.

This permits profile-owned payloads without turning SCLite into a domain schema
registry.

## Review bundles

Use a canonical review bundle when a reviewer needs a portable local view of
the lifecycle. The source bundle is not assumed publishable.

```bash
sclite review examples/govengine-integration --format json --fail-on review
sclite export-review-bundle examples/govengine-integration \
  --mode local_review --output /tmp/review-export.md
```

`public_export` rejects unrecognized files, nested directories, symlinks, hard
links and special files. Redaction/disclosure records describe checks performed;
they do not authorize publication or prove absence of secrets.

## Compatibility

- The Python import package is `sclite`; the distribution is `sclite-core`.
- Current controlled-consumer imports are recorded in
  `sclite/contracts/consumer_imports.v1.json`.
- Reaction, trigger, watchdog and automation modules are absent from SCLite
  2.0; use RExecOp for those mechanics and historical resolution.
- Unknown major schema versions fail closed.
- Artifact schema versions do not track the package version.

See [`SCHEMA_COMPATIBILITY.md`](SCHEMA_COMPATIBILITY.md),
[`PUBLIC_API.md`](PUBLIC_API.md) and
[`GOVENGINE_INTEGRATION_CONTRACT.md`](GOVENGINE_INTEGRATION_CONTRACT.md).

## Non-claims

An integration with SCLite does not by itself prove:

- that an operation was authorized or approved;
- that a signer has a real-world identity;
- that a permit or ticket is fresh;
- that a runtime enforced the verified constraints;
- that referenced raw evidence exists or is truthful;
- that a bundle is safe to publish;
- that network targets, redirects or DNS resolution are within policy.
