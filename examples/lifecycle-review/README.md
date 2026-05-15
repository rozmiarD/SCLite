# Lifecycle review record

This fixture demonstrates the first SCLite lifecycle review aggregate. It reviews the public-safe v0.2 contract lifecycle fixture by combining schema validation, artifact-chain integrity, lifecycle semantic binding, lifecycle-aware Scope Fidelity v0.2, and ticket-use readiness into one public-safe `review_record.v0.1`.

```bash
sclite review-lifecycle sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json --format json
```

The fixture verdict is `review`, not `pass`, because the v0.2 lifecycle bundle predates scoped `execution_ticket.v0.3` ticket-use semantics. This is intentionally conservative.

SCLite does not execute tools, decide legal authorization, prove signer identity, verify carrier delivery, or replace runtime policy.
