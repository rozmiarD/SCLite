# Publication Checklist

This repository is intended to be public-safe, but publication still requires an explicit human decision.

## Required local checks

Run from the repository root:

```bash
python -m sclite.cli validate examples/security-contract-proof
python -m sclite.cli validate-artifact --schema prepared_execution_spec.v0.1 examples/prepared-execution-spec/prepared_execution_spec.json
python -m sclite.cli validate-artifact --schema redacted_prepared_execution_spec.v0.1 examples/security-contract-proof/prepared_execution_spec.redacted.json
python -m sclite.cli validate-artifact --schema scope_fidelity_report.v0.1 examples/scope-fidelity-report/scope_fidelity_report.json
python -m sclite.cli hash-artifact --schema approved_execution_spec.v0.1 examples/security-contract-proof/approved_execution_spec.json
python -m sclite.cli scope-fidelity --approved-spec examples/security-contract-proof/approved_execution_spec.json --fail-on review
python -m sclite.cli validation-receipt examples/security-contract-proof
python -m pytest -q
```

Expected state:

- proof fixture validates;
- Scope Fidelity fixture validates;
- generated Scope Fidelity report exits cleanly;
- validation receipt has `status: passed`;
- pytest passes.

## Residue review

Before public push/package publication, review for:

- credentials or tokens;
- cookies or session material;
- private paths;
- raw stdout/stderr from real runs;
- internal hostnames;
- generated caches;
- virtual environments;
- package build artifacts;
- private runtime logs;
- Ravenclaw workspace-only files;
- live target evidence.

This repository should contain only synthetic examples and public-safe docs/code.

## Claim review

Confirm docs do not claim that SCL v0.1:

- is a standard;
- is a protocol;
- executes tools;
- proves legal authorization;
- proves live vulnerabilities;
- is tamper-proof;
- includes signatures/hash-chain;
- includes OpenClaw/MCP/A2A adapters;
- replaces a runtime policy engine or executor.

## Publication decision

Before any public push:

- confirm repository name/owner;
- confirm remote URL;
- confirm branch to push;
- confirm local git status is clean;
- run the checks above on the exact tree to be pushed;
- get explicit operator approval.

Validation receipts do not authorize publication. They only record checks.
