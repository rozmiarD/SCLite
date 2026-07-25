# GovEngine Integration Contract

This document defines the SCLite lifecycle/review public import surface used by
GovEngine. The packaged `contracts/consumer_imports.v1.json` file records the
reviewed imports used by controlled stack consumers. Downstream dependency
pins and publication remain a separate, coordinated GovEngine/RExecOp/Tecrax
release decision. The inventory records live imports; it does not widen or
rewrite an already published consumer dependency pin.

SCLite remains the artifact/schema/review layer. GovEngine may consume these functions, but SCLite does not become a policy authority, executor, trust authority, carrier adapter, or runtime orchestrator.

## Stable public imports for GovEngine

The current controlled GovEngine source uses these reviewed imports, subject to
its own declared dependency pin:

```python
from sclite.bundles import ReviewBundleError, review_bundle
from sclite.integrity import artifact_descriptor, verify_lifecycle_manifest
from sclite.integrity.chain import ChainVerificationError
from sclite.secure import verify_secure_bundle
from sclite.tickets import (
    TicketSemanticError,
    TicketUseVerificationError,
    validate_ticket_semantics,
    verify_ticket_use,
)
```

The canonical top-level API remains documented in
[`PUBLIC_API.md`](PUBLIC_API.md). Any new GovEngine deep import requires review
and an update to the machine-readable inventory; the superseded proof-trace
helpers and validators are absent.

## Stable CLI surfaces for GovEngine/CI

GovEngine and CI jobs may rely on these kernel CLI commands in SCLite 2.0:

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

Current GovEngine replay decisions prefer the semantic key
`(root_chain_digest, ticket_id|chain_id, key_id)` and retain guard-root-tag
matching only as a compatibility fallback. GovEngine defines the decision
semantics and claim-once port. Replay persistence, TTL, locking, concurrency,
and cleanup remain host-adapter responsibilities. SCLite does not import
GovEngine, keep replay state, or decide runtime admission.

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
