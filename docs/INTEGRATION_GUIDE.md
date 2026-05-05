# Integration Guide

This guide is for runtimes, CLIs, CI jobs, or carrier adapters that want to use SCL artifacts.

SCL core is intentionally small. It provides schemas, validation helpers, redaction helpers, Scope Fidelity review, fixtures, and a CLI. It does not provide a policy gateway, approval system, executor, sandbox, or carrier adapter.

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

A governed runtime can use SCL like this:

1. **Receive scope/input**
   - Runtime receives a target/objective/task.
   - Runtime normalizes it in its own task model.

2. **Evaluate policy**
   - Runtime policy code decides whether preparing execution is allowed.
   - Runtime emits or maps that result into `PolicyDecision`.

3. **Prepare execution shape**
   - Runtime compiles a concrete tool/action shape.
   - Runtime may produce a `PreparedExecutionSpec` and a `RedactedPreparedExecutionSpec` public/auditor view.

4. **Approve**
   - Reviewer/auditor/owner policy approves or rejects the concrete execution shape.
   - Runtime emits `ApprovedExecutionSpec` if approved.

5. **Preflight static host binding**
   - Runtime or CI can build a `ScopeFidelityReport` from the approved spec.
   - `fail` should generally block or require strong review.
   - `review` should generally require inspection.

6. **Execute or dry-run**
   - Runtime executor consumes the approved spec.
   - SCL does not execute it.

7. **Emit receipt/evidence**
   - Runtime emits `ExecutionReceipt` and, where useful, `EvidenceBundle`.
   - Public outputs should keep raw private evidence elsewhere.

8. **Validate**
   - CI/reviewer runs SCL CLI validation.
   - Runtime may emit `SecurityContractValidationReceipt` for its validation bundle.
   - Runtime or CI may emit SCLite artifact hash descriptors for stable content references.
   - Runtime/reporting layer may emit `RedactionPolicy`, `RedactionReceipt`, `PublicValidationSurfaceIndex`, and `PublicSnapshotManifest` artifacts for public review boundaries.

## Minimal Python integration

```python
from sclite.artifacts import validate_artifact
from sclite.scope_fidelity import build_scope_fidelity_report_from_approved_spec

# approved_spec is a dict produced by your runtime.
validate_artifact(approved_spec, "approved_execution_spec.v0.1")

scope_report = build_scope_fidelity_report_from_approved_spec(approved_spec)
if scope_report["verdict"] == "fail":
    raise RuntimeError("approved spec target host drift detected")
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

A carrier-agnostic engine that consumes SCL could expose endpoints such as:

- `POST /policy/decide` -> `PolicyDecision`
- `POST /execution/prepare` -> `PreparedExecutionSpec` + `RedactedPreparedExecutionSpec`
- `POST /execution/approve` -> `ApprovedExecutionSpec`
- `POST /scope-fidelity` -> `ScopeFidelityReport`
- `POST /execution/receipt` -> `ExecutionReceipt`
- `POST /evidence/bundle` -> `EvidenceBundle`
- `POST /validation/receipt` -> `SecurityContractValidationReceipt`
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
