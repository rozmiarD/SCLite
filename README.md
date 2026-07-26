# SCLite

[![CI: pytest](https://github.com/rozmiarD/SCLite/actions/workflows/ci.yml/badge.svg)](https://github.com/rozmiarD/SCLite/actions/workflows/ci.yml)
[![Stable source: sclite-core 2.0.0](https://img.shields.io/badge/stable%20source-sclite--core%202.0.0-blueviolet.svg)](pyproject.toml)
[![PyPI stable: sclite-core 2.0.0](https://img.shields.io/badge/package-sclite--core%202.0.0-blueviolet.svg)](https://pypi.org/project/sclite-core/2.0.0/)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![Contracts: JSON Schema](https://img.shields.io/badge/contracts-JSON%20Schema-informational.svg)](schemas/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

Lightweight Security Contract Layer for auditable operation lifecycles.

SCLite's canonical lifecycle separates what an agent or caller wants, what
policy allows, what was approved, what was executed, and what can be proven.
It is the stack truth layer: it defines, validates, hashes, binds, redacts,
reviews, and verifies artifacts without becoming a runtime, scheduler,
governance authority, domain profile, PKI authority, or raw-evidence store.

## Status

- Version: `2.0.0`
- Release status: **audited and published non-prerelease 2.0.0**
- Project maturity classifier: **Development Status :: 4 - Beta**
- Latest published PyPI package: `sclite-core==2.0.0`
- Python requirement: `>=3.11`; release CI covers Python 3.11, 3.12 and 3.13
- Runtime execution: out of scope; owned by RExecOp or another host runtime
- Protocol/carrier adapters: out of scope; owned by host/runtime integrations
- Integrity: canonical SHA-256 artifact descriptors + ordered hash-linked lifecycle manifest
- Identity/PKI: out of scope for core; owned by the host/governance trust domain
- Security-sensitive descriptor traversal and release tooling: supported and
  tested on Linux; Windows behavior is not claimed

SCLite's core is a **contract/review lifecycle**, not an execution engine.
Runtimes such as RExecOp can consume SCLite artifacts and enforce tickets, but
executors, sandboxes, policy engines, raw evidence storage, agent loops, and
carrier adapters stay outside this package.

## Project sentence

> SCLite separates what an agent wants, what policy allows, what was approved, what was executed, and what can be proven.

## Stack position

| Layer | Ownership |
| --- | --- |
| SCLite | truth, contracts, evidence metadata, receipts, review bundles, digest binding, validation |
| GovEngine | governance, admission, policy decisions, obligations, constraints, enforcement planning |
| RExecOp | domain-neutral lifecycle runner, execution mechanics, connectors, reactions, scheduling, event intake |
| Tecrax and other profiles | domain semantics, intent catalogs, workflow definitions, finding taxonomy, runbooks |

Active maintenance work lives in [`ROADMAP.md`](ROADMAP.md). Package history
lives in [`CHANGELOG.md`](CHANGELOG.md) and the archived
[`docs/archive/ROADMAP_VERSION_HISTORY.md`](docs/archive/ROADMAP_VERSION_HISTORY.md).
Current artifact and schema compatibility references live in
[`docs/ARTIFACTS.md`](docs/ARTIFACTS.md) and
[`docs/SCHEMA_COMPATIBILITY.md`](docs/SCHEMA_COMPATIBILITY.md).

### Extension and ownership boundary

Hosts can pass an explicit `ImmutableSchemaResolver` to `verify_artifact()` for
offline, namespaced domain contracts. Resolver inventories are deterministic
and content-addressed; SCLite performs no plugin discovery, schema download or
global registration. Identifiers use `namespace/name@vN`.

Reaction, trigger, watchdog and automation contracts are owned by RExecOp.
Their former SCLite modules and schemas are absent from SCLite 2.0. Trust and
carrier references have neutral v0.2 forms with opaque namespaced identifiers;
SCLite binds them but does not classify trust, transport, scope or publication
safety.

The packaged consumer-import inventory records reviewed boundaries for
GovEngine, RExecOp and Tecrax; it does not claim that every downstream release
has already updated its dependency pin to SCLite 2.0.

## What problem does SCLite solve?

AI-assisted security workflows often blur separate authority boundaries:

1. a model proposes intent;
2. policy/scope decides whether the request may proceed;
3. code prepares a concrete execution shape;
4. an auditor/reviewer approves or rejects that shape;
5. a runtime executes or dry-runs under bounds;
6. evidence is summarized for review.

SCLite turns those steps into small schema-backed JSON artifacts and verifies
their integrity locally. A reviewer can check a deliberately prepared review
bundle without running live targets or reading private logs. SCLite does not
infer that arbitrary input is safe to publish.

The canonical lifecycle keeps each authority boundary visible:

```mermaid
flowchart LR
    A[intent_contract] --> B[policy_decision]
    B --> C[execution_contract]
    C --> D[execution_ticket]
    D --> E[execution_receipt]
    E --> F[evidence_contract]
    F --> G[artifact_chain_manifest]
```

## v0.2 canonical lifecycle

```text
intent_contract -> policy_decision -> execution_contract -> execution_ticket -> execution_receipt -> evidence_contract -> artifact_chain_manifest
```

Current v0.2 artifacts:

| Artifact | Purpose |
| --- | --- |
| `IntentContract` | Captures what an agent/caller wants before authority exists. |
| `PolicyDecision` v0.2 | Captures allow/deny/review policy outcome bound to intent. |
| `ExecutionContract` | Captures the exact bounded execution shape prepared for review. |
| `ExecutionTicket` | Captures approval for one exact execution contract under explicit bounds and validity. |
| `ExecutionReceipt` v0.2 | Captures what an external runtime reports as executed or dry-run. |
| `EvidenceContract` | Captures receipt-bounded claims, non-claims, replay, verification, and evidence links without storing raw evidence. |
| `ArtifactChainManifest` | Ordered tamper-evident hash chain over lifecycle artifacts. |

Verify the lifecycle fixture:

```bash
sclite validate-chain --example contract-lifecycle-v0.2
sclite verify-lifecycle --example contract-lifecycle-v0.2
```

`--example contract-lifecycle-v0.2` resolves the fixture packaged in the
installed distribution, so these commands work from an empty directory after
installation. Filesystem manifest paths remain supported for your own
artifacts.

`validate-chain` verifies the ordered hash-chain. `verify-lifecycle` applies
the lifecycle gate on top and requires the exact canonical v0.2 role sequence
with no extra roles, duplicate roles, or changed order.

The summary output intentionally distinguishes these postures:

- `validate-chain ...` reports `posture=integrity_only` and
  `lifecycle_not_checked`;
- `verify-lifecycle ...` and `validate-chain --strict-lifecycle ...` report
  `posture=strict_lifecycle` after lifecycle semantics pass.

## What the verifiers check

The v0.2 `validate-chain` verifier checks local chain integrity:

- manifest paths cannot escape the artifact root;
- artifact descriptors match canonical SHA-256 digests;
- hash-chain links and root digest recompute correctly.

`verify-lifecycle` and `validate-chain --strict-lifecycle` add strict lifecycle
semantics:

- lifecycle artifacts must appear in the canonical order;
- no extra roles, duplicate roles, or reordered lifecycle roles are accepted;
- policy, execution contract, ticket, receipt, and evidence digest links are
  checked across the lifecycle.
- policy binds the correct intent digest;
- ticket binds the correct execution contract digest;
- receipt binds the correct execution ticket and execution contract digests;
- evidence contract binds the correct receipt and execution ticket digests.
- each canonical lifecycle role carries the expected artifact type,
  `schema_version`, and packaged `schema_ref` for strict/secure profiles.

Loose `validate-chain` keeps compatibility for generic hash-chain manifests.
It may report duplicate, missing, or extra lifecycle roles in JSON, but those
role-shape findings become fail-closed only when strict lifecycle is requested.

## JSON Schema validation modes

SCLite has two validation modes:

| Mode | Dependency | Intended use | Boundary |
| --- | --- | --- | --- |
| dependency-free subset validator | none | fast/offline local checks and minimal installs | only supports the keyword subset SCLite implements directly |
| strict Draft 2020-12 validator | optional `jsonschema` extra | CI, release gates, and reviewer validation | uses `jsonschema.Draft202012Validator` |

The default CLI path preserves the zero-runtime-dependency package. Release and CI validation must also run strict mode through `scripts/strict_schema_gate.sh`. See [SCLite Validation](VALIDATION.md) for the supported keyword table and strict-mode commands.

All production JSON input paths use the same strict dependency-free loader.
It rejects duplicate object keys, non-standard `NaN`/`Infinity` numbers and
invalid UTF-8 before schema or digest checks. `VerificationLimits` supplies
finite defaults for per-file and aggregate bytes, nesting depth, parsed nodes
and manifest entries; Python hosts can pass an explicit policy when a reviewed
artifact class needs different bounds.

## What SCLite is

SCLite core is limited to:

```text
define / validate / hash / bind / redact / review / verify
```

The review-bundle shape first published on the 0.5.x line remains part of the
current lifecycle/review front door: it packages lifecycle artifacts, review
records, and verification receipts for local public-safe review. The
scoped-ticket surface still bounds what a runtime may consume, and
`verify-ticket-use` checks that public-safe evidence stays inside the linked
receipt. Review records and guarded secure-bundle verification now consume
that same static ticket-use check when v0.3 ticket, receipt, and evidence
artifacts are present. See [`ROADMAP.md`](ROADMAP.md).

It provides:

- JSON schemas for current lifecycle, review, profile, and publication-hygiene artifacts;
- deterministic artifact hashing helpers;
- v0.2 lifecycle/chain verification;
- scoped-ticket review helpers (`validate-ticket`, plus the
  `sclite-devtools explain-ticket` inspection command);
- ticket-use / receipt-bounded-evidence checks (`verify-ticket-use`);
- digest-bound trust/carrier profile reference checks (`validate-trust-profile`, `validate-carrier-profile`);
- lifecycle review records and Scope Fidelity v0.2 checks (`review-lifecycle`);
- canonical review-bundle validation and Markdown export (`review`, `export-review-bundle`);
- redaction/public-snapshot helper artifacts;
- kernel CLIs (`sclite` and `scl`) for validation/verification and a separate
  `sclite-devtools` entrypoint for non-production inspection and fixture tools.

The typed Python front door consists of `verify_artifact()` and
`verify_bundle()`. `verify_bundle()` requires an explicit `VerificationPolicy`
and never infers a security posture from its input. The returned frozen result
types are structured verification outcomes, not authority or authentication
tokens. See [`docs/PUBLIC_API.md`](docs/PUBLIC_API.md).

Review-bundle inspection and publication use separate modes. `review` keeps
`local_review` compatibility and reports the complete recursive inventory.
`export-review-bundle` defaults to fail-closed `public_export`, which rejects
unrecognized files, nested directories, symlinks, hard links and special files. Programmatic
materialization stages and verifies a complete bundle before publishing it by
rename; replacing an existing target requires explicit `overwrite=True`.

The package stays centered on local validation, review, profile references, and integrity checks:

Disclosure/publication helpers use the monotonic status model `unknown →
operator_asserted → checks_performed → externally_verified`. Unknown inputs and
arbitrary CLI files default to `unknown`; heuristic redaction names its checks
but does not claim credentials or private paths are absent. SCLite 2.0 does not
derive a `public_safe` boolean from this status. No status authorizes
publication: that remains a separate host/operator step.

Canonical results contain relative path labels. `verify-secure-bundle
--local-debug --format json` is the explicit local-only escape hatch for an
absolute-path debug envelope.

```mermaid
flowchart TB
    CLI[CLI] --> Validation[validation]
    CLI --> ReviewBundles[review bundles]
    CLI --> Profiles[profiles]
    Validation --> Schemas[schemas]
    Validation --> Artifacts[artifacts]
    Artifacts --> Integrity[integrity chain]
    Artifacts --> Tickets[tickets]
    ReviewBundles --> Integrity
    ReviewBundles --> ScopeFidelity[scope fidelity]
    ReviewBundles --> Profiles
    Profiles --> Integrity
```

## Out of Scope

SCLite intentionally does not own:

| Capability | Owner |
| --- | --- |
| Execution, subprocess handling, connectors, scheduler/event intake, reaction loop | RExecOp or another host runtime |
| Governance, admission, policy decisions, obligations, constraints, human sign-off gates | GovEngine |
| Infrastructure/security/business semantics, findings, runbooks, target taxonomy | Tecrax or another domain profile |
| Raw evidence storage, secret storage, replay store, operational logs | Host/operator infrastructure |
| Signer identity, PKI trust, KMS, transparency log guarantees | Host/governance trust domain |
| Legal authorization or proof of live vulnerability evidence | Operator/governance process |

Execution and runtime lifecycle belong to RExecOp. Governance and admission
belong to GovEngine. Raw evidence, replay persistence and concrete trust
verification remain host/operator responsibilities:

```text
profile intent/workflow
        |
        v
RExecOp lifecycle -----> GovEngine governance/admission
        |
        v
RExecOp execution and runtime facts
        |
        v
SCLite artifacts -> validation -> review/verification result
```

## Retired proof-trace path

The older public-safe proof trace was a migration source during alpha
development. It is out of scope for the installed/current SCLite surface.
Retained schema identifiers such as `review_record.v0.1` identify current
formats and are not compatibility product lines.

See [`SPEC.md`](SPEC.md) for the canonical model, artifact definitions,
integrity chain, compatibility notes, and explicit security boundaries. See
[`SECURITY_MODEL.md`](SECURITY_MODEL.md) and
[`docs/SECURITY_PROFILES.md`](docs/SECURITY_PROFILES.md) for the frozen
security profile meanings, Kernel Guard transcript/canonicalization freeze,
and replay/non-claim boundaries for the 2.0 release line.

## Project docs

- [`ROADMAP.md`](ROADMAP.md) — active 2.0 maintenance and freeze policy.
- [`docs/archive/ROADMAP_VERSION_HISTORY.md`](docs/archive/ROADMAP_VERSION_HISTORY.md) — historical pre-2.0 roadmap.
- [`SECURITY_MODEL.md`](SECURITY_MODEL.md) — security guarantees, non-claims, Kernel Guard transcript freeze, replay boundary, and key-rotation boundary.
- [`docs/SECURITY_PROFILES.md`](docs/SECURITY_PROFILES.md) — stable profile matrix for `integrity_only`, `strict_lifecycle`, `guarded_domain_auth`, `guarded-strict`, and host-owned freshness.
- [`docs/PUBLIC_API.md`](docs/PUBLIC_API.md) — current top-level Python API exports and typed verification front door.
- [`docs/SCHEMA_COMPATIBILITY.md`](docs/SCHEMA_COMPATIBILITY.md) — schema-version matrix, unknown-field policy, artifact ID guidance, and GovEngine compatibility notes.
- [`docs/TRUST_PROFILES.md`](docs/TRUST_PROFILES.md) — digest-bound trust reference profiles without PKI/trust authority ownership.
- [`docs/CARRIER_PROFILES.md`](docs/CARRIER_PROFILES.md) — digest-bound carrier reference profiles without adapter/transport ownership.
- [`docs/REVIEW_RECORDS.md`](docs/REVIEW_RECORDS.md) — static lifecycle review records and Scope Fidelity v0.2.
- [`docs/REVIEW_BUNDLES.md`](docs/REVIEW_BUNDLES.md) — canonical v0.5 review-bundle shape and CLI.
- [`docs/GOVENGINE_INTEGRATION_CONTRACT.md`](docs/GOVENGINE_INTEGRATION_CONTRACT.md) — current SCLite imports, CLI surfaces, and fixtures for GovEngine.
- [`docs/CLI_EXIT_CODES.md`](docs/CLI_EXIT_CODES.md) — CLI exit-code contract for CI/downstream callers.
- [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) — concrete tampering, boundary, and non-goal model.
- [`PUBLIC_STATUS.md`](PUBLIC_STATUS.md) — current maturity and non-claims.
- [`VALIDATION.md`](VALIDATION.md) — local validation and build gates.
- [`PUBLICATION_CHECKLIST.md`](PUBLICATION_CHECKLIST.md) — release/publication checklist.
- [`CHANGELOG.md`](CHANGELOG.md) — notable package changes.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribution and boundary rules.
- [`SECURITY.md`](SECURITY.md) — security reporting and fixture-safety policy.

## Installation

Install the latest published package from PyPI with an exact version pin:

```bash
python -m pip install sclite-core==2.0.0
```

Install directly from GitHub:

```bash
pip install git+https://github.com/rozmiarD/SCLite.git
```

From a local checkout:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

Runtime dependencies are intentionally empty. The `dev` extra installs the
test, strict-schema, typing, coverage and lint tools used by local gates.
Python import package remains `sclite`.

Run the canonical local development gate:

```bash
scripts/dev_gate.sh
```

## CLI quickstart

Validate the v0.2 lifecycle chain:

```bash
sclite validate-chain --example contract-lifecycle-v0.2
sclite verify-lifecycle --example contract-lifecycle-v0.2
```

Use `sclite validate-chain --strict-lifecycle ...` when a generic chain check
should also fail closed on the canonical lifecycle role sequence.

Optionally verify a GovEngine/KERNEL-domain guard sidecar:

```bash
SCLITE_KERNEL_GUARD_KEY='local-test-secret-at-least-32-bytes' \
  sclite verify-guarded-chain \
  /path/to/artifact_chain_manifest.json \
  --guard /path/to/kernel_guard_manifest.json \
  --strict-lifecycle
```

`kernel_guard_hmac_v1` authenticates a manifest and its entries only inside the
domain that knows the HMAC secret. It is not PKI, non-repudiation, public
identity, replay prevention, or proof that a runtime behaved correctly.
Production build and verification require a `str` or `bytes` key of at least
32 bytes after UTF-8 encoding. Results always report
`key_entropy_status="not_checked"`: SCLite enforces a length floor, not
randomness, custody, rotation or KMS policy. `verify-guarded-chain` alone offers
`--legacy-read-only-key-policy` for historical short-key verification; that
mode reports `legacy_read_only_guard`, never `guarded_domain_auth`.
When `--guard` is provided explicitly, SCLite resolves it relative to the
current working directory, not relative to the bundle directory. Omitting
`--guard` uses `kernel_guard_manifest.json` next to the manifest or review
bundle target.

For runtime-consumable guarded bundles, use the fail-closed secure profile
instead of assembling the weaker pieces manually. The guard sidecar is produced
by the trusted host/GovEngine domain and is not committed in the public example
bundle:

```bash
SCLITE_KERNEL_GUARD_KEY='local-test-secret-at-least-32-bytes' \
  sclite verify-secure-bundle examples/govengine-integration \
  --guard /path/to/kernel_guard_manifest.json
```

`verify-secure-bundle` is the `guarded-strict` profile. It always verifies the
artifact chain, requires the exact lifecycle role sequence, requires
`kernel_guard_hmac_v1`, binds manifest metadata, and fails when the guard is
missing. It still does not check replay freshness. GovEngine defines the
deterministic replay decision and claim-once port; a production host adapter
must provide atomic, durable replay state. Current GovEngine decisions prefer
the semantic binding `(root_chain_digest, ticket_id|chain_id, key_id)` and use
guard-root-tag matching only as a compatibility fallback.

JSON output includes a stable `verification_result` object with explicit layer
statuses:

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

The `verification_result.v1` contract makes SCLite's non-claims
machine-readable; it does not add replay state, public identity, or runtime
enforcement.

For new Python integrations, `verify_secure_bundle_result()` is the production
front door and returns an immutable `VerificationResult`. Serialize it with
`serialize_verification_result()` to the additive `verification_result.v1.1`
contract, which records `bundle_digest`, verifier policy/version and the checks
actually performed. The type reduces accidental misuse; it is not an
authentication token and can be instantiated or forged inside Python. A host
must re-verify the source bundle or authenticate the serialized result through
a separately trusted channel.

`verify_secure_bundle()` and its embedded `verification_result.v1` dictionary
remain for compatibility. Raw all-pass fixture construction lives in
`sclite.testing`; the old builder name remains an alias through 2.0 and performs
no verification.

Security posture modes:

- `integrity_only`: local SHA-256 artifact-chain consistency only.
- `strict_lifecycle`: integrity plus exact lifecycle roles, no extras,
  duplicates, or reorder.
- `guarded_domain_auth`: strict lifecycle plus HMAC authenticity inside the
  domain that knows the secret.
- `guarded_domain_auth_fresh`: HMAC authenticity plus GovEngine replay-decision
  semantics over host-owned atomic replay state.
- `public_signed_export`: future public signature/export mode, not implemented
  in this release.

Validate and explain the v0.3 scoped-ticket fixture:

```bash
sclite validate-ticket \
  sclite/examples/scoped-ticket-v0.3/execution_ticket.json \
  --contract sclite/examples/scoped-ticket-v0.3/execution_contract.json
sclite-devtools explain-ticket sclite/examples/scoped-ticket-v0.3/execution_ticket.json
sclite verify-ticket-use \
  sclite/examples/scoped-ticket-v0.3/execution_ticket.json \
  --contract sclite/examples/scoped-ticket-v0.3/execution_contract.json \
  --receipt sclite/examples/scoped-ticket-v0.3/execution_receipt.json \
  --evidence-contract sclite/examples/scoped-ticket-v0.3/evidence_contract.json
```

Validate one artifact against a schema:

```bash
sclite validate-artifact \
  --schema execution_contract.v0.2 \
  examples/review-bundle/03_execution_contract.json
```

Use strict Draft 2020-12 validation with the optional `jsonschema` extra:

```bash
pip install 'sclite-core[jsonschema]'
sclite validate-artifact \
  --strict-jsonschema \
  --schema execution_contract.v0.2 \
  examples/review-bundle/03_execution_contract.json
```

Hash one artifact with deterministic SCLite canonical JSON + SHA-256:

```bash
sclite-devtools hash-artifact \
  --schema execution_contract.v0.2 \
  examples/review-bundle/03_execution_contract.json
```

Generate a standalone Scope Fidelity report from explicit dry-run shape facts:

```bash
sclite-devtools scope-fidelity \
  --target https://example.com/login \
  --normalized-arg https://example.com/login
```

This explicit-fields example produces a static report whose verdict is
`review`; use `--fail-on review` in CI when that verdict should return exit 2.

Review and export the v0.5 review-bundle fixture:

```bash
sclite review examples/review-bundle --format json
sclite export-review-bundle examples/review-bundle --format markdown
```

Review bundles package the lifecycle chain into a reviewer-facing record and optional Markdown export:

```mermaid
flowchart LR
    Bundle[review bundle directory] --> Shape[validate shape]
    Shape --> Chain[verify chain]
    Chain --> Lifecycle[lifecycle review]
    Lifecycle --> Record[review_record]
    Record --> Markdown[markdown export]
```

Review the GovEngine integration-readiness fixture and enforce conservative CI thresholds:

```bash
sclite review examples/govengine-integration --format json --fail-on review
sclite validate-trust-profile examples/govengine-integration/trust_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json
sclite validate-carrier-profile examples/govengine-integration/carrier_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json
```

Run tests:

```bash
python -m pytest -q
```

## Python usage

Verify a v0.2 lifecycle manifest:

```python
from sclite.integrity import verify_artifact_chain_manifest

# Load artifact_chain_manifest.json as a dict and verify it against a local root.
result = verify_artifact_chain_manifest(manifest, root=fixture_dir)
assert result["status"] == "passed"
```

Review scoped-ticket / receipt-bounded-evidence fixtures:

```python
from sclite.tickets import validate_ticket_semantics, verify_ticket_use

checks = validate_ticket_semantics(ticket, execution_contract)
assert "ticket_scope_matches_execution_contract" in checks

result = verify_ticket_use(ticket, execution_contract, execution_receipt, evidence_contract)
assert "evidence_claims_bounded_by_receipt" in result["checks"]
```

Review a canonical v0.5 bundle:

```python
from sclite.bundles import review_bundle

record = review_bundle("examples/govengine-integration")
assert record["verdict"] == "pass"
```

## Repository layout

```text
sclite/                         Python package
sclite/schemas/                 Packaged schemas
sclite/examples/contract-lifecycle-v0.2/
sclite/examples/review-bundle/  Packaged v0.5 review-bundle fixture
sclite/examples/govengine-integration/ Packaged downstream integration fixture
examples/review-bundle/         Public v0.5 review-bundle fixture
examples/govengine-integration/ Public GovEngine integration-readiness fixture
schemas/                        Source schema copies
SPEC.md                         Current public specification
CHANGELOG.md                    Release notes
```

## License

MIT. See [`LICENSE`](LICENSE).
