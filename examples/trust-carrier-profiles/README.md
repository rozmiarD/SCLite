# Trust and carrier profile references

This fixture demonstrates SCLite v0.4-style sidecar references bound to the published v0.3 scoped-ticket artifact.

```bash
sclite validate-trust-profile sclite/examples/trust-carrier-profiles/trust_profile_ref.json --subject sclite/examples/scoped-ticket-v0.3/execution_ticket.json
sclite validate-carrier-profile sclite/examples/trust-carrier-profiles/carrier_profile_ref.json --subject sclite/examples/scoped-ticket-v0.3/execution_ticket.json
```

SCLite validates shape and digest binding only. External runtimes/verifiers decide trust, transport, delivery, revocation, and authority.
