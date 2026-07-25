# Scoped Ticket v0.3 Fixture

This fixture demonstrates an `ExecutionTicket` v0.3 scoped ticket bound to a public-safe v0.2 execution contract, receipt, and evidence contract. It is runtime-consumable only as a local accountability artifact; it does not prove legal authorization, signer trust, runtime enforcement, or live vulnerability evidence.

Review it with:

```bash
sclite validate-ticket sclite/examples/scoped-ticket-v0.3/execution_ticket.json --contract sclite/examples/scoped-ticket-v0.3/execution_contract.json
sclite-devtools explain-ticket sclite/examples/scoped-ticket-v0.3/execution_ticket.json
sclite verify-ticket-use \
  sclite/examples/scoped-ticket-v0.3/execution_ticket.json \
  --contract sclite/examples/scoped-ticket-v0.3/execution_contract.json \
  --receipt sclite/examples/scoped-ticket-v0.3/execution_receipt.json \
  --evidence-contract sclite/examples/scoped-ticket-v0.3/evidence_contract.json
```

`verify-ticket-use` is a static Receipt-Bounded Evidence check. It verifies that the receipt binds the ticket and execution contract, that runtime/mode/network/use counts stay inside the ticket, and that evidence claims are explicitly bounded by the receipt via `source_receipt_id`. It also rejects completed-execution, executed-command, or network-execution claims that the linked receipt cannot support. It does not run a tool or attest that a runtime enforced the ticket.
