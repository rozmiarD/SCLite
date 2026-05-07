# SCLite

[![CI](https://github.com/rozmiarD/SCLite/actions/workflows/ci.yml/badge.svg)](https://github.com/rozmiarD/SCLite/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![Package: sclite 0.2.0](https://img.shields.io/badge/package-sclite%200.2.0-blueviolet.svg)](pyproject.toml)
[![JSON Schema](https://img.shields.io/badge/contracts-JSON%20Schema-informational.svg)](schemas/)

Lightweight Security Contract Layer for auditable AI/security contract lifecycles.

SCLite v0.2 separates what an agent wants, what policy allows, what was approved, what was executed, and what can be proven.

## Status

- Version: `0.2.0`
- Status: **draft lifecycle candidate**
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

`verify-lifecycle` currently uses the same verifier as `validate-chain`; the name exists because it describes the v0.2 review action more clearly.

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

It provides:

- JSON schemas for lifecycle and compatibility artifacts;
- deterministic artifact hashing helpers;
- v0.2 lifecycle/chain verification;
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

## Installation

Once published to PyPI, the intended install path is:

```bash
pip install sclite
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

```python
from sclite.integrity import verify_artifact_chain_manifest

# Load artifact_chain_manifest.json as a dict and verify it against a local root.
result = verify_artifact_chain_manifest(manifest, root=fixture_dir)
assert result["status"] == "passed"
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
