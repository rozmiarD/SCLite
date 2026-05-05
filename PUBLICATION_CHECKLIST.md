# Publication Checklist

Before public push/package publication:

- Run `python -m scl.cli validate examples/security-contract-proof`.
- Run `python -m scl.cli validate-artifact --schema scope_fidelity_report.v0.1 examples/scope-fidelity-report/scope_fidelity_report.json`.
- Run `python -m scl.cli scope-fidelity --approved-spec examples/security-contract-proof/approved_execution_spec.json --fail-on review`.
- Run `python -m pytest -q`.
- Review for credentials, cookies, auth headers, private paths, raw stdout/stderr, internal hostnames, tokens, and generated artifacts.
- Confirm no live target execution, protocol adapter work, or public push is implied by validation receipts.
- Push only after explicit operator approval.
