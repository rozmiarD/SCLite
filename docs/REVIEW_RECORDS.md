# Review Records

SCLite review records are static, public-safe lifecycle review aggregates. They are the review result format used by lifecycle reviews and v0.5 review bundles.

A `review_record.v0.1` summarizes:

- declared artifact schema validation;
- artifact-chain integrity;
- lifecycle semantic binding;
- lifecycle-aware Scope Fidelity v0.2;
- scoped ticket-use readiness;
- explicit non-claims.

## Boundary

SCLite review records do **not**:

- execute tools;
- decide legal authorization;
- prove signer identity;
- verify carrier delivery;
- make runtime policy decisions;
- replace GovEngine or a domain runtime.

They are reviewer-facing evidence summaries over already-existing artifacts.

## CLI

```bash
sclite review-lifecycle \
  sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json \
  --format json
```

Markdown output is also available:

```bash
sclite review-lifecycle \
  sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json \
  --format markdown
```

## Conservative verdicts

Review records use the same verdict vocabulary as Scope Fidelity:

- `pass`
- `review`
- `fail`

The bundled lifecycle-review fixture returns `review` because the v0.2 lifecycle fixture predates scoped `execution_ticket.v0.3` ticket-use semantics. That is intentional: a complete chain can still need reviewer attention when newer downstream semantics are unavailable.

## Scope Fidelity v0.2

Scope Fidelity v0.2 compares explicit lifecycle target references across:

- intent contract;
- policy decision;
- execution contract;
- execution ticket.

Execution receipts and evidence contracts are treated as digest-linked lifecycle artifacts rather than independent target authorities unless they expose explicit targets. This keeps the check static and conservative.

Scope Fidelity is a drift check, not a scope authority. It does not resolve DNS, redirects, wildcard scope, CIDR/IP ranges, IPv6, IDN/punycode, port boundaries, subdomain policy, eTLD+1, localhost/private-network policy, or URL canonicalization edge cases. Runtime policy layers such as GovEngine or Ravenclaw must decide whether work is authorized.
