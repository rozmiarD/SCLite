# Scoped Ticket v0.3 Fixture

This fixture demonstrates an `ExecutionTicket` v0.3 scoped ticket bound to the public-safe v0.2 execution contract fixture. It is runtime-consumable only as a local accountability artifact; it does not prove legal authorization, signer trust, runtime enforcement, or live vulnerability evidence.

Review it with:

```bash
sclite validate-ticket sclite/examples/scoped-ticket-v0.3/execution_ticket.json --contract sclite/examples/scoped-ticket-v0.3/execution_contract.json
sclite explain-ticket sclite/examples/scoped-ticket-v0.3/execution_ticket.json
```
