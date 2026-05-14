# SCLite

[![CI: pytest](https://github.com/rozmiarD/SCLite/actions/workflows/ci.yml/badge.svg)](https://github.com/rozmiarD/SCLite/actions/workflows/ci.yml)
[![Package: sclite-core 0.3.5](https://img.shields.io/pypi/v/sclite-core?label=package%3A%20sclite-core&color=blueviolet)](https://pypi.org/project/sclite-core/)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![Contracts: JSON Schema](https://img.shields.io/badge/contracts-JSON%20Schema-informational.svg)](schemas/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

Lightweight Security Contract Layer for auditable AI/security contract lifecycles.


SCLite v0.2 separates what an agent wants, what policy allows, what was approved, what was executed, and what can be proven.

## Status

- Version: `0.3.5`
- Status: **published 0.3.x scoped-ticket and receipt-bounded-evidence line**
- Runtime execution: not included
- Protocol/carrier adapters: not included
- Integrity: canonical SHA-256 artifact descriptors + ordered hash-linked lifecycle manifest
- Identity/PKI: not included in core

SCLite v0.2 is a **contract lifecycle**, not an execution engine. Runtimes such as Ravenclaw can consume SCLite artifacts and enforce tickets, but executors, sandboxes, policy engines, raw evidence storage, agent loops, and carrier adapters stay outside this package.

## Project sentence

> SCLite separates what an agent wants, what policy allows, what was approved, what was executed, and what can be proven.

## What problem does SCLite solve?

AI-assisted security workflows often blur separate authority boundaries:

1. a model proposes intent;
2. policy/scope decides whether the request may proceed;
3. code prepares a concrete execution shape;
4. an auditor/reviewer approves or rejects that shape;
5. a runtime executes or dry-runs under bounds;
6. evidence is summarized for review.

SCLite turns those steps into small schema-backed JSON artifacts and verifies their integrity locally. A reviewer can check the public-safe bundle without running live targets or reading private logs.

## v0.2 canonical lifecycle

```text
intent_contract -> policy_decision -> execution_contract -> execution_ticket -> execution_receipt -> evidence_contract -> artifact_chain_manifest
```

Current v0.2 artifacts:

| Artifact | Purpose |
| --- | --- |
| `IntentContract` | Captures what an agent/caller wants before authority exists. |
| `PolicyDecision` v0.2 | Captures allow/deny/review policy outcome bound to intent. |
| `ExecutionContract` | Captures the exact bounded execution shape prepared for review. |
| `ExecutionTicket` | Captures approval for one exact execution contract under explicit bounds and validity. |
| `ExecutionReceipt` v0.2 | Captures what an external runtime reports as executed or dry-run. |
| `EvidenceContract` | Captures public-safe claims, non-claims, replay, verification, and evidence links. |
| `ArtifactChainManifest` | Ordered tamper-evident hash chain over lifecycle artifacts. |

Verify the lifecycle fixture:

```bash
sclite validate-chain sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json
sclite verify-lifecycle sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json
```

`verify-lifecycle` uses the same underlying verifier as `validate-chain`; the command name exists because it describes the v0.2 review action more clearly.

## What the verifier checks

The v0.2 verifier checks more than raw hashes:

- manifest paths cannot escape the artifact root;
- artifact descriptors match canonical SHA-256 digests;
- hash-chain links and root digest recompute correctly;
- lifecycle artifacts appear in the canonical order;
- policy binds the correct intent digest;
- ticket binds the correct execution contract digest;
- receipt binds the correct execution ticket digest;
- evidence contract binds the correct receipt digest.

## What SCLite is

SCLite core is limited to:

```text
define / validate / hash / bind / redact / verify
```

Roadmap direction: scoped tickets should bound what a runtime may consume, and receipts should bound what public-safe evidence may claim. See [`ROADMAP.md`](ROADMAP.md).

It provides:

- JSON schemas for lifecycle and compatibility artifacts;
- deterministic artifact hashing helpers;
- v0.2 lifecycle/chain verification;
- scoped-ticket review helpers (`validate-ticket`, `explain-ticket`);
- ticket-use / receipt-bounded-evidence checks (`verify-ticket-use`);
- redaction/public-snapshot helper artifacts;
- a CLI for local validation and review fixtures;
- legacy v0.1 compatibility fixtures and schemas.

## What SCLite is not

SCLite is not:

- a security scanner;
- an executor;
- a sandbox;
- a full policy engine;
- an approval authority by itself;
- an agent loop;
- a tool wrapper package for `nmap`, `ffuf`, etc.;
- an MCP/OpenClaw/A2A protocol replacement;
- a proof of legal authorization;
- a proof of live vulnerability evidence;
- a proof of signer identity or PKI trust;
- a tamper-proof transparency log.

## Legacy v0.1 compatibility

The older public-safe v0.1 proof trace remains supported:

```text
scope/input -> policy decision -> prepared execution spec -> approved execution spec -> dry-run execution receipt -> evidence summary
```

v0.1 compatibility artifacts remain available for existing integrations, including Ravenclaw public proof fixtures. New lifecycle work should use the v0.2 model.

See [`SPEC.md`](SPEC.md) for the canonical model, artifact definitions, integrity chain, compatibility notes, and explicit security boundaries.

## Project docs

- [`ROADMAP.md`](ROADMAP.md) — planned accountability-layer evolution using PEP 440-compatible milestone labels.
- [`PUBLIC_STATUS.md`](PUBLIC_STATUS.md) — current maturity and non-claims.
- [`VALIDATION.md`](VALIDATION.md) — local validation and build gates.
- [`PUBLICATION_CHECKLIST.md`](PUBLICATION_CHECKLIST.md) — release/publication checklist.
- [`CHANGELOG.md`](CHANGELOG.md) — notable package changes.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribution and boundary rules.
- [`SECURITY.md`](SECURITY.md) — security reporting and fixture-safety policy.

## Installation

Install from PyPI:

```bash
pip install sclite-core
```

Install directly from GitHub:

```bash
pip install git+https://github.com/rozmiarD/SCLite.git
```

From a local checkout:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

Runtime dependencies are intentionally empty. The `dev` extra installs `pytest` for local tests.

## CLI quickstart

Validate the v0.2 lifecycle chain:

```bash
sclite validate-chain sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json
sclite verify-lifecycle sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json
```

Validate and explain the v0.3 scoped-ticket fixture:

```bash
sclite validate-ticket \
  sclite/examples/scoped-ticket-v0.3/execution_ticket.json \
  --contract sclite/examples/scoped-ticket-v0.3/execution_contract.json
sclite explain-ticket sclite/examples/scoped-ticket-v0.3/execution_ticket.json
sclite verify-ticket-use \
  sclite/examples/scoped-ticket-v0.3/execution_ticket.json \
  --contract sclite/examples/scoped-ticket-v0.3/execution_contract.json \
  --receipt sclite/examples/scoped-ticket-v0.3/execution_receipt.json \
  --evidence-contract sclite/examples/scoped-ticket-v0.3/evidence_contract.json
```

Validate the legacy public-safe proof fixture:

```bash
sclite validate examples/security-contract-proof
```

Validate one artifact against a schema:

```bash
sclite validate-artifact \
  --schema prepared_execution_spec.v0.1 \
  examples/prepared-execution-spec/prepared_execution_spec.json
```

Use strict Draft 2020-12 validation with the optional `jsonschema` extra:

```bash
pip install 'sclite-core[jsonschema]'
sclite validate-artifact \
  --strict-jsonschema \
  --schema prepared_execution_spec.v0.1 \
  examples/prepared-execution-spec/prepared_execution_spec.json
```

Hash one artifact with deterministic SCLite canonical JSON + SHA-256:

```bash
sclite hash-artifact \
  --schema approved_execution_spec.v0.1 \
  examples/security-contract-proof/approved_execution_spec.json
```

Generate a Scope Fidelity report from the approved spec fixture:

```bash
sclite scope-fidelity \
  --approved-spec examples/security-contract-proof/approved_execution_spec.json \
  --fail-on review
```

Emit a validation receipt for the proof fixture:

```bash
sclite validation-receipt examples/security-contract-proof
```

Run tests:

```bash
python -m pytest -q
```

## Python usage

Verify a v0.2 lifecycle manifest:

```python
from sclite.integrity import verify_artifact_chain_manifest

# Load artifact_chain_manifest.json as a dict and verify it against a local root.
result = verify_artifact_chain_manifest(manifest, root=fixture_dir)
assert result["status"] == "passed"
```

Review scoped-ticket / receipt-bounded-evidence fixtures:

```python
from sclite.tickets import validate_ticket_semantics, verify_ticket_use

checks = validate_ticket_semantics(ticket, execution_contract)
assert "ticket_scope_matches_execution_contract" in checks

result = verify_ticket_use(ticket, execution_contract, execution_receipt, evidence_contract)
assert "evidence_claims_bounded_by_receipt" in result["checks"]
```

## Repository layout

```text
sclite/                         Python package
sclite/schemas/                 Packaged schemas
sclite/examples/contract-lifecycle-v0.2/
examples/security-contract-proof/ Legacy v0.1 public-safe proof fixture
schemas/                        Source schema copies
SPEC.md                         v0.2 draft specification
CHANGELOG.md                    Release notes
```

## License

MIT. See [`LICENSE`](LICENSE).
