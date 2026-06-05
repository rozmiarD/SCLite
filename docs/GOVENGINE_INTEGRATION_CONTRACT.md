# GovEngine Integration Contract

This document defines the SCLite lifecycle/review public import surface that
the currently published GovEngine package line may rely on. Published
GovEngine still declares `sclite-core>=0.8.0b2,<0.9`; SCLite `1.0.0` keeps
this surface source-compatible, but downstream dependency widening is a
separate GovEngine/Ravenclaw release decision.

SCLite remains the artifact/schema/review layer. GovEngine may consume these functions, but SCLite does not become a policy authority, executor, trust authority, carrier adapter, or runtime orchestrator.

## Stable public imports for GovEngine

GovEngine may rely on the following import paths in the
`sclite-core>=0.8.0b2,<0.9` line and in the SCLite `1.0.x` source-compatible
surface:

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

GovEngine and CI jobs may rely on these CLI commands in the currently
published downstream range and in the SCLite `1.0.x` source-compatible
surface:

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
    "scope_fidelity_verdict": "pass|review|fail"
  },
  "checks": [],
  "non_claims": []
}
```

GovEngine should treat any verdict other than `pass` as requiring block/review unless a higher-level profile explicitly permits a weaker result.

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
