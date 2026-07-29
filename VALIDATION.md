# SCLite Validation

This document describes the gates for the current `sclite-core==2.0.1` source:
the unpublished non-prerelease 2.0.1 release source; publication pending.
Repository code, packaged schemas, tests and executable validators are
authoritative. Historical release prose is not a current compatibility source.

## Canonical development gate

From an editable development install:

```bash
python -m pip install -e '.[dev]'
scripts/dev_gate.sh
```

`scripts/dev_gate.sh` runs:

1. `scripts/public_validation_gate.sh`;
2. `scripts/strict_schema_gate.sh`;
3. `scripts/security_regression_gate.sh`;
4. `python scripts/validate_public_truth.py`;
5. the complete pytest suite.

Run static checks separately:

```bash
python -m ruff check .
python -m mypy
node scripts/verify_vectors.mjs conformance/sclite-2.0-vectors.json
```

## Public truth and documentation anti-drift

```bash
python scripts/validate_public_truth.py
python -m pytest -q tests/test_public_truth.py tests/test_consumer_contracts.py \
  tests/test_cli_surface_split.py tests/test_packaged_fixture_sync.py
```

Together, the validator and targeted tests above check:

- distribution/import/version and published install truth;
- frozen top-level exports and the controlled-consumer import inventory;
- current artifact fixtures and retired 1.x surface absence;
- active Markdown links and referenced test paths;
- documented CLI command lines against the actual kernel/devtools registry;
- current 2.0 wording and removed-surface context;
- 2.0 consumer-inventory disposition semantics;
- source/package fixture parity and non-authority claims.

Changelog and `docs/archive/` are historical records and are excluded from
current-wording checks.

## CLI surface

Kernel commands use `sclite`, `scl` or `python -m sclite.kernel_cli`:

```bash
python -m sclite.kernel_cli validate-chain \
  sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json
python -m sclite.kernel_cli verify-lifecycle \
  sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json
python -m sclite.kernel_cli validate-ticket \
  sclite/examples/scoped-ticket-v0.3/execution_ticket.json \
  --contract sclite/examples/scoped-ticket-v0.3/execution_contract.json
python -m sclite.kernel_cli verify-ticket-use \
  sclite/examples/scoped-ticket-v0.3/execution_ticket.json \
  --contract sclite/examples/scoped-ticket-v0.3/execution_contract.json \
  --receipt sclite/examples/scoped-ticket-v0.3/execution_receipt.json \
  --evidence-contract sclite/examples/scoped-ticket-v0.3/evidence_contract.json
python -m sclite.kernel_cli review \
  examples/govengine-integration --format json --fail-on review
python -m sclite.kernel_cli export-review-bundle \
  examples/govengine-integration --mode local_review --format markdown
python -m sclite.kernel_cli validate-artifact \
  --schema redaction_policy.v0.2 \
  examples/redaction-policy/redaction_policy.json
```

Inspection and fixture commands use `sclite-devtools` or
`python -m sclite.devtools`:

```bash
python -m sclite.devtools explain-ticket \
  sclite/examples/scoped-ticket-v0.3/execution_ticket.json
python -m sclite.devtools hash-artifact \
  --schema execution_contract.v0.2 \
  examples/review-bundle/03_execution_contract.json
python -m sclite.devtools review-lifecycle \
  sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json \
  --format json
python -m sclite.devtools scope-fidelity \
  --target https://example.com/login \
  --normalized-arg https://example.com/login \
  --fail-on review
```

Each entrypoint rejects commands owned by the other surface. See
[`docs/CLI_EXIT_CODES.md`](docs/CLI_EXIT_CODES.md).

## Schema validation

The default dependency-free validator implements the documented packaged-schema
subset. The strict release gate uses `jsonschema.Draft202012Validator`:

```bash
scripts/public_validation_gate.sh
scripts/strict_schema_gate.sh
```

Supported keywords and version combinations are documented in
[`docs/SCHEMA_COMPATIBILITY.md`](docs/SCHEMA_COMPATIBILITY.md). Unknown major
versions fail closed. Artifact `schema_ref` values resolve to packaged schemas
unless external resolution is explicitly enabled.

Untrusted artifact and review-bundle JSON input paths use bounded loaders that
reject duplicate keys, invalid UTF-8, `NaN`/`Infinity`, excessive depth/node
counts and configured byte/inventory limits.

## Security regression

```bash
scripts/security_regression_gate.sh
```

The gate covers descriptor/path boundaries, strict lifecycle semantics, Kernel
Guard transcript binding, guarded bundle verification, JSON limits, schema
resolution and extension resolver behavior.

Security posture is layered:

- `validate-chain` reports integrity only;
- `verify-lifecycle` adds exact lifecycle semantics;
- `verify-guarded-chain` adds shared-secret guard authentication;
- `verify-secure-bundle` requires guarded-strict verification.

SCLite reports replay as `not_checked`. Production replay stores should provide
atomic check-and-set behavior outside SCLite. Explicit `--guard` paths are
resolved relative to the caller's current working directory; omitted guard
paths resolve next to the selected manifest/bundle. Path validation rejects
manifest and Kernel Guard sidecar paths that escape the selected root.

Kernel Guard transcript/canonicalization changes require a new profile name.

## Python verification

Preferred typed front door:

```python
from sclite import VerificationPolicy, verify_artifact, verify_bundle
```

`verify_bundle()` requires an explicit policy. Python callers using lower-level
chain APIs can use `verify_lifecycle_manifest()` or pass
`require_lifecycle=True` where supported; generic chain verification does not
silently imply lifecycle verification.

Machine-readable secure outcomes use the frozen `verification_result.v1`
contract with the additive `verification_result.v1.1` serializer.

The frozen top-level Python import surface for the 2.0 line is documented in
[`docs/PUBLIC_API.md`](docs/PUBLIC_API.md).

## Consumer compatibility

The machine-readable controlled-consumer contract is
`sclite/contracts/consumer_imports.v1.json`.

```bash
python -m sclite.consumer_contracts --imports-only
python scripts/validate_forbidden_consumer_imports.py \
  ../govengine ../rexecop ../tecrax
```

Each consumer keeps its own exact dependency pin. SCLite source compatibility
does not claim that an already published consumer artifact has adopted a newer
pin. The second command scans the live sibling checkouts for retired SCLite
imports; it is intentionally separate from the repo-local public-truth
validator.

## Package and release gates

Package smoke is opt-in release-readiness evidence only:

```bash
scripts/package_smoke.sh
scripts/reproducible_build_gate.sh
scripts/release_ab_repro_gate.sh
```

These gates build wheel/sdist artifacts, run `twine check`, install into clean
environments, run `pip check`, validate entrypoints/import inventory and compare
reproducible outputs. The source tree must not contain stale `build/`, `dist/`
or egg-info artifacts when the package smoke starts.

Before publication also run:

```bash
python scripts/validate_external_review.py --help
python scripts/validate_release_record_commit.py --help
```

Release workflows bind tag/version, reviewed source commit and built artifacts.
The profile freeze docs must remain aligned, and any incompatible security
profile change requires a new profile identity.

## Expected result

A release candidate is acceptable only when all of the following agree:

- source version, package metadata and public truth;
- kernel/devtools CLI registry and examples;
- packaged schemas, source schemas and conformance vectors;
- consumer import inventory and live controlled-consumer imports;
- wheel/sdist contents and clean-install behavior;
- external review and release evidence;
- documentation claims and non-claims.
