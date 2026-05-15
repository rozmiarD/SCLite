# SCLite review bundle demo

This is the canonical SCLite v0.5 review-bundle fixture. It packages the public-safe lifecycle artifacts, a hash-linked artifact-chain manifest, reviewer Markdown, and a verification receipt.

```bash
sclite review examples/review-bundle --format json
sclite export-review-bundle examples/review-bundle --format markdown
```

The fixture verdict is `review` because it uses the v0.2 lifecycle ticket rather than the newer scoped `execution_ticket.v0.3` ticket-use profile. The conservative verdict is intentional.

SCLite validates and reviews the bundle locally; it does not execute tools, decide authorization, prove signer identity, verify carrier delivery, or replace a runtime policy engine.
