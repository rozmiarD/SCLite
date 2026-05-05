# Security Contract Layer

Security Contract Layer (SCL) is a small JSON-first package for validating security-operation contract artifacts and public-safe proof traces.

It turns proposed AI/security actions into auditable contracts, receipts, evidence, and validation results. The v0.1 chain is:

`scope -> policy -> contract -> receipt -> evidence -> validate`

## v0.1 scope

- JSON/dict-first artifact helpers.
- JSON schema validation for current v0.1 artifacts.
- Clean synthetic proof fixtures under `examples/security-contract-proof/`.
- Generic public-safe redaction/sanitization helpers.
- Neutral `ScopeFidelityReport` v0.1 static host-binding review.
- Standalone CLI for fixture validation, artifact validation, scope-fidelity reports, and validation receipts.

## Non-goals and limitations

- SCL v0.1 is not a standard.
- SCL v0.1 is not a protocol.
- SCL v0.1 does not execute tools.
- SCL v0.1 does not prove live exploitation.
- SCL v0.1 does not include cryptographic signatures.
- SCL v0.1 does not include a hash-chain.
- SCL v0.1 does not include a strong identity or approver model.
- Runtime-specific policy, auditor orchestration, and execution engines belong in integrations that consume SCL, not in SCL core.

## Local commands

From this directory:

```bash
python -m scl.cli validate examples/security-contract-proof
python -m scl.cli validate-artifact --schema approved_execution_spec.v0.1 examples/security-contract-proof/approved_execution_spec.json
python -m scl.cli scope-fidelity --approved-spec examples/security-contract-proof/approved_execution_spec.json
python -m scl.cli validation-receipt examples/security-contract-proof
python -m pytest -q
```

From the Ravenclaw repository root, compatibility scripts may wrap this package for Ravenclaw-local validation. Those wrappers are integration code, not SCL core.

## Scope Fidelity

`ScopeFidelityReport` is a carrier-neutral static review artifact. It compares a target host with hosts detected in normalized arguments and execution-plan steps, then returns:

- `pass` for exact detected host binding;
- `review` when no host is detectable from the execution shape;
- `fail` when cross-host drift is detected.

It does not resolve DNS, follow redirects, prove program authorization, or execute tools.

## License

MIT.
