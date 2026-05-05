# Security Contract Layer v0.1 Draft Spec

Status: draft v0.1. This is not a standard and not a protocol.

SCL defines schema-backed artifacts for governed security/agentic execution:

- `PolicyDecision`
- `PreparedExecutionSpec` / redacted prepared spec view (schema TBD)
- `ApprovedExecutionSpec`
- `ExecutionReceipt`
- `EvidenceBundle`
- `ScopeFidelityReport`
- `SecurityContractValidationReceipt`

Canonical public-safe proof trace:

`scope/input -> policy decision -> prepared execution spec -> approved execution spec -> dry-run execution receipt -> evidence summary`

## Non-claims

- SCL does not execute tools.
- SCL does not prove legal authorization.
- SCL does not prove live vulnerabilities.
- SCL is not tamper-proof; v0.1 has no signatures or hash-chain.
- SCL is carrier-neutral payload/schema/validation infrastructure, not an OpenClaw/MCP/A2A replacement.
