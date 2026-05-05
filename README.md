# Security Contract Layer

Security Contract Layer (SCL) is a small, JSON-first contract layer for making security/agentic execution reviewable before and after a tool run.

It is currently a **draft v0.1** Python package, CLI, schema set, and fixture bundle. It does **not** execute tools, prove authorization, prove live vulnerabilities, or replace a runtime. It gives runtimes and carriers a common artifact shape for answering questions like:

- What did the agent or caller intend to do?
- What did policy decide before execution was prepared?
- What execution shape was approved?
- What compact receipt summarizes what happened or would have happened?
- What evidence/non-claims can a reviewer validate without seeing private runtime logs?
- Did the requested target host drift from the hosts detected in the execution shape?

The practical goal is simple: **model intent should not become execution authority by itself**. SCL is the contract/evidence layer that a governed runtime can consume.

## Status

- Version: `0.1.0`
- Status: draft / candidate standalone repository
- License: MIT
- Runtime execution: not included
- Protocol/carrier adapters: not included
- Cryptographic integrity: not included in v0.1

This repository is intended to be the reusable SCL core. A runtime such as Ravenclaw can use it as a dependency and keep policy engines, approval flows, executors, and carrier adapters outside this package.

## What problem does SCL solve?

AI-assisted security workflows often compress several very different steps into one ambiguous action:

1. a model proposes intent;
2. policy/scope decides whether that intent is allowed;
3. code prepares a concrete execution shape;
4. a reviewer/auditor approves or rejects it;
5. an executor runs or dry-runs tools;
6. evidence is summarized for another human/system.

Without structured artifacts, these steps are easy to blur together. A chat transcript or log line may say “approved” or “safe”, but a reviewer still has to reconstruct what was approved, what target was bound, what command shape existed, and what the output is claiming.

SCL separates those concerns into schema-backed JSON artifacts. The current v0.1 artifacts are intentionally small and public-safe so they can be checked in fixtures, CI, docs, or review bundles without publishing raw private evidence.

## What SCL is

SCL is:

- a set of JSON schemas for governed execution artifacts;
- a Python package for building and validating current v0.1 artifacts;
- a CLI for validating fixtures and generating static review artifacts;
- a public-safe proof fixture showing the expected artifact chain;
- a neutral `ScopeFidelityReport` helper for static host-binding review.

## What SCL is not

SCL is not:

- a security scanner;
- an executor;
- an approval authority by itself;
- a full policy engine;
- a runtime sandbox;
- a new protocol;
- an MCP/OpenClaw/A2A replacement;
- a proof of legal authorization;
- a proof of live vulnerability evidence;
- a tamper-proof audit chain.

Those may be implemented by systems that consume SCL, but they are not part of this v0.1 core.

## Current artifact model

The public-safe proof trace is:

```text
scope/input -> policy decision -> prepared execution spec -> approved execution spec -> dry-run execution receipt -> evidence summary
```

Current schema-backed v0.1 artifacts:

| Artifact | Purpose | Current status |
| --- | --- | --- |
| `PolicyDecision` | Captures policy outcome such as allow/deny/review-before-prepare with scope/tool facts. | Schema + fixture validation. |
| `ApprovedExecutionSpec` | Captures the approved execution shape and execution truth expected by a runtime executor. | Schema + fixture validation. |
| `ExecutionReceipt` | Compact, public-safe summary of dry-run/execution outcome. | Schema + fixture validation. |
| `EvidenceBundle` | Public-safe evidence/non-claim summary for the proof trace. | Schema + fixture validation. |
| `ScopeFidelityReport` | Static review of target host vs hosts detected in normalized args/execution plan. | Schema + builder + CLI + fixture. |
| `SecurityContractValidationReceipt` | Receipt showing which local/public-safe SCL validation checks ran. | Schema + builder + CLI. |

Current non-schema artifact in the proof fixture:

| Artifact | Purpose | Current status |
| --- | --- | --- |
| `prepared_execution_spec.redacted.json` | Public/auditor-facing view of a prepared execution shape. | Fixture + redaction helper. Dedicated schema is still future work. |

See [`SPEC.md`](SPEC.md) and [`docs/ARTIFACTS.md`](docs/ARTIFACTS.md) for more detail.

## Installation

From a local checkout:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

Runtime dependencies are intentionally empty for v0.1. The `dev` extra installs `pytest` for local tests.

## CLI quickstart

Validate the public-safe proof fixture:

```bash
python -m scl.cli validate examples/security-contract-proof
```

Validate one artifact against a schema:

```bash
python -m scl.cli validate-artifact \
  --schema approved_execution_spec.v0.1 \
  examples/security-contract-proof/approved_execution_spec.json
```

Generate a Scope Fidelity report from the approved spec fixture:

```bash
python -m scl.cli scope-fidelity \
  --approved-spec examples/security-contract-proof/approved_execution_spec.json \
  --fail-on review
```

Emit a validation receipt for the proof fixture:

```bash
python -m scl.cli validation-receipt examples/security-contract-proof
```

Run tests:

```bash
python -m pytest -q
```

## Python usage

Build a static Scope Fidelity report:

```python
from scl.scope_fidelity import build_scope_fidelity_report, validate_scope_fidelity_report

report = build_scope_fidelity_report(
    target="https://example.com",
    normalized_args=["https://example.com/login"],
    execution_plan=[{"tool": "http_probe", "args": ["https://example.com/login"]}],
    target_in_scope=True,
    source_artifact="example",
)
validate_scope_fidelity_report(report)
print(report["verdict"])  # "pass"
```

Validate an artifact:

```python
import json
from pathlib import Path
from scl.artifacts import validate_artifact

artifact = json.loads(Path("examples/security-contract-proof/approved_execution_spec.json").read_text())
validate_artifact(artifact, "approved_execution_spec.v0.1")
```

## Scope Fidelity in plain language

`ScopeFidelityReport` is a static host-binding check. It compares:

- the declared target host; with
- hosts detected in normalized arguments; and
- hosts detected in execution-plan steps, including simple line-based stdin values.

It returns:

- `pass` when detected hosts exactly match the target host;
- `review` when no host is detectable from the execution shape;
- `fail` when a different host appears.

It does **not** resolve DNS, follow redirects, inspect files loaded at runtime, parse every possible payload encoding, prove ownership, or prove legal authorization. Treat it as a preflight/reviewer artifact, not as a scope engine.

## Repository layout

```text
.
├── schemas/                         # top-level schemas for reviewers/tools
├── examples/                        # clean synthetic public-safe examples
├── scl/                             # Python package
│   ├── schemas/                     # packaged schema copies
│   ├── examples/                    # packaged example copies
│   ├── artifacts.py                 # schema loading, validation, proof-trace helpers
│   ├── hosts.py                     # small dependency-free host extraction helpers
│   ├── redaction.py                 # generic public-safe sanitization
│   ├── scope_fidelity.py            # ScopeFidelityReport builder/validator
│   ├── validation.py                # fixture + validation receipt helpers
│   └── cli.py                       # CLI entrypoint
├── tests/                           # package tests
├── SPEC.md                          # draft v0.1 spec narrative
└── PUBLICATION_CHECKLIST.md         # pre-publish safety checklist
```

Top-level `schemas/` and `examples/` are duplicated into `scl/` package data so both humans and installed Python code can access them.

## Integration model

A governed runtime should treat SCL as a dependency, not as its executor. One possible integration sequence is:

1. runtime receives scope/input;
2. policy engine emits or maps a `PolicyDecision`;
3. runtime prepares an execution shape;
4. reviewer/auditor approves an `ApprovedExecutionSpec`;
5. runtime executor consumes the approved spec;
6. runtime emits an `ExecutionReceipt`;
7. reporting layer emits an `EvidenceBundle` and/or validation receipt.

SCL core helps with schema-backed artifact shape, fixture validation, generic redaction, and static host-binding review. The runtime remains responsible for real scope policy, tool allowlists, approval authority, execution isolation, logging, and private evidence storage.

See [`docs/INTEGRATION_GUIDE.md`](docs/INTEGRATION_GUIDE.md).

## Public-safe examples

The fixtures use `example.com`, dry-run semantics, and synthetic metadata. They are designed to show shape and validation behavior, not live operational value.

Important non-claims:

- no live target execution;
- no live vulnerability evidence;
- no raw private stdout/stderr;
- no credentials or private local paths;
- no protocol adapter implementation.

## Roadmap candidates

Likely future work, not present v0.1 guarantees:

- dedicated schema for `PreparedExecutionSpec` and `RedactedPreparedExecutionSpec`;
- canonical JSON/hash helpers;
- optional receipt signing or hash-chain support;
- stronger redaction policy/receipt artifacts;
- adapters/reference integrations in separate packages;
- replacement of the lightweight JSON Schema subset validator with a full JSON Schema implementation if needed.

## License

MIT.
