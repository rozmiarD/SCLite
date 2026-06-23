# GovEngine Integration Contract

This document defines the SCLite lifecycle/review public import surface used by
GovEngine. Published GovEngine `0.15.0` and the `0.16.0` source candidate both
declare `sclite-core>=1.0.3,<1.1`. Raising consumer release floors remains a
separate, coordinated GovEngine/RExecOp/Tecrax release decision.

SCLite remains the artifact/schema/review layer. GovEngine may consume these functions, but SCLite does not become a policy authority, executor, trust authority, carrier adapter, or runtime orchestrator.

## Stable public imports for GovEngine

GovEngine may rely on the following import paths in the current
`sclite-core>=1.0.3,<1.1` supported range:

```python
from sclite.integrity import artifact_descriptor, verify_artifact_chain_manifest
from sclite.tickets import validate_ticket_semantics, verify_ticket_use
from sclite.review import build_review_record_from_manifest
from sclite.bundles import materialize_review_bundle, review_bundle, validate_review_bundle_shape
from sclite.profiles import validate_trust_profile_ref, validate_carrier_profile_ref
from sclite.scope_fidelity import build_lifecycle_scope_fidelity_report
from sclite.secure import verify_secure_bundle
```

Anything not listed here is internal or not guaranteed as a stable GovEngine integration surface. `sclite.artifacts` remains importable for schema validation and canonical hashes; the superseded proof-trace helpers and validators have been removed.

## Stable CLI surfaces for GovEngine/CI

GovEngine and CI jobs may rely on these CLI commands in the current SCLite
`1.0.x` supported range:

```bash
sclite validate-chain PATH/TO/artifact_chain_manifest.json
sclite verify-lifecycle PATH/TO/artifact_chain_manifest.json
sclite validate-ticket PATH/TO/execution_ticket.json --contract PATH/TO/execution_contract.json
sclite verify-ticket-use PATH/TO/execution_ticket.json --contract PATH/TO/execution_contract.json --receipt PATH/TO/execution_receipt.json --evidence-contract PATH/TO/evidence_contract.json
sclite validate-trust-profile PATH/TO/trust_profile_ref.json --subject PATH/TO/subject.json
sclite validate-carrier-profile PATH/TO/carrier_profile_ref.json --subject PATH/TO/subject.json
sclite review PATH/TO/review-bundle --format json
sclite export-review-bundle PATH/TO/review-bundle --format markdown
```

See [`CLI_EXIT_CODES.md`](CLI_EXIT_CODES.md) for exit-code semantics.

## Machine-readable review contract

`review_bundle()` and `sclite review --format json` return a `review_record.v0.1` object with these stable fields:

```json
{
  "artifact_type": "review_record",
  "schema_version": "v0.1",
  "verdict": "pass|review|fail",
  "summary": {
    "artifact_count": 6,
    "root_chain_digest": "...",
    "scope_fidelity_verdict": "pass|review|fail",
    "ticket_use_status": "pass|review|fail",
    "ticket_use_applicability": "verified|not_applicable|incomplete"
  },
  "checks": [],
  "non_claims": []
}
```

GovEngine should treat any verdict other than `pass` as requiring block/review
unless an explicit GovEngine policy permits a weaker review posture. SCLite and
domain profiles do not authorize execution.

## Integration fixture

The canonical downstream fixture is:

```text
examples/govengine-integration/
```

It demonstrates:

- v0.2 lifecycle artifact order;
- v0.3 scoped execution ticket;
- dry-run receipt;
- receipt-bounded evidence;
- digest-bound trust/carrier sidecars;
- review-record verification receipt;
- review verdict `pass`.

The fixture is synthetic and public-safe. It does not execute tools or prove authorization.

## Host freshness handoff

`verify_secure_bundle()` gives GovEngine a deterministic local verifier result
for `guarded-strict`: artifact chain, strict lifecycle, Kernel Guard HMAC, and
manifest metadata binding. That result is necessary but insufficient for a
runtime freshness decision.

GovEngine or another host should atomically claim freshness using stable
inputs shaped like:

```json
{
  "root_chain_digest": "<artifact-chain root digest>",
  "guard_root_tag": "<kernel_guard_hmac_v1 root tag>",
  "chain_id": "<manifest chain_id>",
  "key_id": "<guard key_id>",
  "ticket_id": "<execution_ticket.ticket_id>",
  "run_id": "<GovEngine-owned run/admission id>",
  "observed_at": "<GovEngine observation timestamp>",
  "host_admission_context": "<GovEngine policy/admission reference>",
  "verifier_profile": "guarded-strict"
}
```

Replay persistence, TTL, concurrency, cleanup, and rejection policy remain
host-owned. SCLite does not import GovEngine, keep replay state, or decide
runtime admission.

## Optional downstream smoke

The repo-local compatibility smoke is:

```bash
python -m pytest tests/test_govengine_integration_surface.py -q -p no:cacheprovider
```

It verifies the documented import surface, public-safe GovEngine fixture, and
CLI commands without importing GovEngine. If a downstream GovEngine checkout is
available, run that project's own dependency-widening smoke after installing
this SCLite tree, but keep the dependency one-way: GovEngine may import SCLite;
SCLite production code must not import GovEngine.
