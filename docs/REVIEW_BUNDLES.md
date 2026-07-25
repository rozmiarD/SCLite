# Review Bundles

SCLite review bundles are the v0.5 packaging surface for lifecycle artifacts and their local verification result.

They make SCLite understandable and demoable without GovEngine, RExecOp,
protocol adapters or any live runtime. The `examples/govengine-integration/`
bundle is the current downstream integration-readiness fixture.

## Review flow

```mermaid
flowchart LR
    Directory[review bundle directory] --> Shape[validate canonical shape]
    Shape --> Chain[verify artifact chain]
    Chain --> Lifecycle[run lifecycle review]
    Lifecycle --> Record[review_record]
    Record --> Export[Markdown export]
```

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

`README.md` is the only optional file recognized by the default public-export
inventory. Any other sidecar must remain in `local_review` unless a future
version explicitly gives it a public-export contract.

`REVIEW.md` and `verification_receipt.json` are required canonical sidecars for packaged examples, but callers should treat them as cached review outputs. The `sclite review` and `sclite export-review-bundle` commands regenerate review output from the current lifecycle artifacts and manifest; they do not trust a stale sidecar as authority.

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

`export-review-bundle` defaults to `--mode public_export`. This mode recursively
inventories the directory and fails on extras, hidden or nested files,
case/Unicode name variants, symlinks, directories and special files. To inspect
a local owner-extended bundle without claiming a closed public surface, use:

```bash
sclite export-review-bundle examples/govengine-integration \
  --mode local_review --format markdown
```

Write Markdown to a file:

```bash
sclite export-review-bundle examples/review-bundle --format markdown --output REVIEW.generated.md
```

## GovEngine integration fixture

`examples/govengine-integration/` uses the same canonical shape but includes the v0.3 scoped ticket, dry-run receipt, receipt-bounded evidence, and digest-bound trust/carrier sidecars that GovEngine can consume without taking over SCLite validation.

Those trust/carrier files are intentionally reported as extra inventory by
`local_review`; they are not silently promoted into SCLite's closed-world
public-export allowlist.

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

## Atomic materialization

`materialize_review_bundle()` writes every canonical file into a temporary
sibling directory, fsyncs files, rebuilds and verifies the review record,
validates the selected inventory mode, fsyncs the staged directory and only
then renames it into place. The default is `mode="public_export"` and
`overwrite=False`.

If the target already exists, the caller must pass `overwrite=True`. The old
directory is moved aside, the complete stage is renamed into place, and a
failed publish restores the old directory. SCLite does not implement backups,
remote storage or a general filesystem sandbox.

## Boundary

SCLite review bundles do **not**:

- execute tools;
- decide legal authorization;
- prove signer identity;
- verify carrier delivery;
- make runtime policy decisions;
- replace GovEngine, RExecOp, Tecrax or another profile/runtime.

They package public-safe proof artifacts and local review output.
