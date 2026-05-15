# SCLite GovEngine integration fixture

This public-safe fixture is the canonical SCLite 0.5.1 downstream integration bundle for GovEngine. It combines the v0.2 lifecycle, a v0.3 scoped execution ticket, dry-run receipt, receipt-bounded evidence, a review-record verification receipt, and digest-bound trust/carrier sidecars.

```bash
sclite review examples/govengine-integration --format json
sclite validate-trust-profile examples/govengine-integration/trust_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json
sclite validate-carrier-profile examples/govengine-integration/carrier_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json
```

Expected review verdict: `pass`. SCLite still does not execute tools, decide authorization, prove PKI trust, or verify carrier delivery.
