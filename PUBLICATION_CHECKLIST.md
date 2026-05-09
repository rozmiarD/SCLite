# Publication Checklist

This repository is intended to be public-safe, but publication still requires an explicit human decision.

## Identity guard

For maintainer releases from the operator-controlled publish tree, verify the effective repo-local Git identity:

```bash
git config --get user.name
git config --get user.email
```

Required maintainer value for this publish tree:

```text
0x505badc0de <32790662+rozmiarD@users.noreply.github.com>
```

External contributors should use their own GitHub-associated identity; this guardrail is not a contributor identity requirement.

History transparency guardrail: never rewrite already-published history to fix authorship, contribution graphs, cleanup, or cosmetics. No force-push, date rewrite, or tag rewrite for published public history; use corrective commits instead.

## Required local checks

Run from the repository root:

```bash
python -m sclite.cli validate examples/security-contract-proof
python -m sclite.cli validate-artifact --schema prepared_execution_spec.v0.1 examples/prepared-execution-spec/prepared_execution_spec.json
python -m sclite.cli validate-artifact --schema redacted_prepared_execution_spec.v0.1 examples/security-contract-proof/prepared_execution_spec.redacted.json
python -m sclite.cli validate-artifact --schema scope_fidelity_report.v0.1 examples/scope-fidelity-report/scope_fidelity_report.json
python -m sclite.cli hash-artifact --schema approved_execution_spec.v0.1 examples/security-contract-proof/approved_execution_spec.json
python -m sclite.cli validate-artifact --schema redaction_policy.v0.1 examples/redaction-policy/redaction_policy.json
python -m sclite.cli validate-artifact --schema redaction_receipt.v0.1 examples/redaction-receipt/redaction_receipt.json
python -m sclite.cli validate-artifact --schema public_validation_surface_index.v0.1 examples/public-validation-surface-index/public_validation_surface_index.json
python -m sclite.cli validate-artifact --schema public_snapshot_manifest.v0.1 examples/public-snapshot-manifest/public_snapshot_manifest.json
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

Confirm docs do not claim that SCLite/SCL v0.2:

- is a standard;
- is a protocol;
- executes tools;
- proves legal authorization;
- proves live vulnerabilities;
- is tamper-proof;
- includes signatures/hash-chain;
- includes OpenClaw/MCP/A2A adapters;
- replaces a runtime policy engine or executor.

## Package build checks

Before any TestPyPI or PyPI upload, run from a clean tree:

```bash
python -m pip install build twine
python -m build
python -m twine check dist/*
```

Then test-install the generated wheel in a clean environment.

Do not commit `build/`, `dist/`, `*.egg-info`, caches, or virtual environments.

## Publication decision

Before any public push:

- confirm repository name/owner;
- confirm remote URL;
- confirm branch to push;
- confirm local git status is clean;
- run the checks above on the exact tree to be pushed;
- confirm the PyPI distribution name is `sclite-core` and the Python import package remains `sclite`;
- decide whether the release remains on the current version or becomes a patch release;
- get explicit operator approval for any tag, TestPyPI upload, or PyPI upload.

Validation receipts do not authorize publication. They only record checks.
