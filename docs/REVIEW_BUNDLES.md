# Review Bundles

SCLite review bundles are the v0.5 packaging surface for lifecycle artifacts and their local verification result.

They make SCLite understandable and demoable without Ravenclaw, GovEngine, OpenClaw, MCP, A2A, or any live runtime. The `examples/govengine-integration/` bundle is the current downstream integration-readiness fixture.

## Canonical shape

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

The numbered artifacts are the lifecycle payloads. `artifact_chain_manifest.json` binds them by canonical SHA-256 descriptors and ordered chain digests. `verification_receipt.json` is a `review_record.v0.1` generated from the bundle. `REVIEW.md` is a reviewer-friendly export of that record.

## CLI

Review a bundle and emit JSON:

```bash
sclite review examples/review-bundle --format json
```

Emit a compact summary:

```bash
sclite review examples/review-bundle --format summary
```

Export reviewer Markdown:

```bash
sclite export-review-bundle examples/review-bundle --format markdown
```

Write Markdown to a file:

```bash
sclite export-review-bundle examples/review-bundle --format markdown --output REVIEW.generated.md
```

## GovEngine integration fixture

`examples/govengine-integration/` uses the same canonical shape but includes the v0.3 scoped ticket, dry-run receipt, receipt-bounded evidence, and digest-bound trust/carrier sidecars that GovEngine can consume without taking over SCLite validation.

```bash
sclite review examples/govengine-integration --format json --fail-on review
sclite validate-trust-profile examples/govengine-integration/trust_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json
sclite validate-carrier-profile examples/govengine-integration/carrier_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json
```

`examples/bad-review-bundle-cross-host/` is intentionally failing and exists for negative tests around target drift.

## Conservative verdicts

Bundle reviews use:

- `pass`
- `review`
- `fail`

The bundled example currently returns `review` because it demonstrates the v0.2 canonical lifecycle fixture, whose ticket predates scoped `execution_ticket.v0.3` ticket-use semantics. That is intentional. SCLite should ask for reviewer attention instead of overclaiming a pass when newer downstream checks are unavailable.

## Boundary

SCLite review bundles do **not**:

- execute tools;
- decide legal authorization;
- prove signer identity;
- verify carrier delivery;
- make runtime policy decisions;
- replace GovEngine, Ravenclaw, Tecrax, or another runtime.

They package public-safe proof artifacts and local review output.
