# Audit Verification 2026-06-01

This document records the verification of an externally supplied SCLite audit
against the real repository state at branch `audit/sclite-release-truth-20260601`.
The audit was treated as a hypothesis; repository files, CLI output, tests, and
validation scripts were treated as ground truth.

## Claim Classification

| ID | Audit claim | Evidence inspected | Status | Severity | Fix |
| --- | --- | --- | --- | --- | --- |
| AV-01 | SCLite has a clear non-runtime/non-PKI/non-replay boundary. | `README.md`, `SPEC.md`, `SECURITY_MODEL.md`, `sclite/verification_result.py`, `sclite/kernel_guard.py` | CONFIRMED | LOW | no |
| AV-02 | Kernel Guard uses HMAC-SHA256, requires `key_id`, validates the artifact chain before accepting guarded material, and uses constant-time tag comparison. | `sclite/kernel_guard.py`, `tests/test_kernel_guard.py`, `tests/test_secure_bundle.py` | CONFIRMED | LOW | no |
| AV-03 | Manifest/review/bundle path traversal is guarded by resolving paths under the selected root. | `sclite/integrity/chain.py`, `sclite/review.py`, `sclite/bundles.py`, negative tests | CONFIRMED | LOW | no |
| AV-04 | The main SCLite CLI/core does not expose a subprocess/os.system execution surface. | `sclite/cli.py`, `rg subprocess`, `rg os.system` | CONFIRMED | LOW | no |
| AV-05 | `pyproject.toml` still says `version = "0.3.5"` while source/docs claim `1.0.0`. | `pyproject.toml`, `sclite/__init__.py`, `scripts/validate_public_truth.py` | REFUTED | CRITICAL if true | no |
| AV-06 | The repo's public truth gate should fail on `pyproject_version_mismatch`. | `.venv/bin/python scripts/validate_public_truth.py` | REFUTED | CRITICAL if true | no |
| AV-07 | GitHub Actions still use `actions/checkout@v4` and `actions/setup-python@v5`. | `.github/workflows/ci.yml`, `scripts/validate_public_truth.py` | REFUTED | HIGH if true | no |
| AV-08 | GitHub Actions still run retired CLI commands such as `sclite validate` and `sclite validation-receipt`. | `.github/workflows/ci.yml`, `sclite/cli.py`, CLI `--help` | REFUTED | HIGH if true | no |
| AV-09 | `validate-chain` is documented as generic hash-chain validation, but default verification also runs lifecycle semantics for canonical role sets. | `sclite/integrity/chain.py`, `README.md`, `SPEC.md`, `VALIDATION.md`, CLI JSON output | CONFIRMED | MEDIUM | yes |
| AV-10 | `schema_ref` resolution is too liberal because bundle/local files can override packaged schemas through `root / raw_ref` or `repo_root() / raw_ref`. | `sclite/artifacts.py`, call sites in chain/review/kernel guard | CONFIRMED | HIGH | yes |
| AV-11 | The only SCLite/GovEngine integration test is callable-import-only. | `tests/test_govengine_integration_surface.py`, `tests/test_review_bundles.py`, `scripts/public_validation_gate.sh`, `scripts/strict_schema_gate.sh` | PARTIALLY_CONFIRMED | MEDIUM | yes |
| AV-12 | SCLite has no meaningful GovEngine fixture compatibility coverage. | review-bundle tests, profile-ref tests, public/strict gates | REFUTED | MEDIUM if true | no |
| AV-13 | Published GovEngine dependency range has not been widened to SCLite `1.0.0`, despite SCLite stable publication. | `docs/GOVENGINE_INTEGRATION_CONTRACT.md`, operator-home truth, downstream package range docs | PARTIALLY_CONFIRMED | LOW | docs |
| AV-14 | Overall numeric score/maturity rating. | Subjective audit conclusion, not a repository invariant | NOT_TESTABLE_FROM_REPO | LOW | no |

## Remediation Roadmap

| ID | Problem | Evidence | Risk | Required change | Files | Validation | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R1 | Untrusted artifact `schema_ref` can load local schema files by default. | AV-10 | A bundle can weaken schema validation by shipping a permissive schema under a trusted-looking path. | Prefer packaged schemas by default; require explicit API opt-in for external schemas; keep CLI explicit `--schema PATH` as operator-controlled opt-in. | `sclite/artifacts.py`, `sclite/cli.py`, `SECURITY_MODEL.md`, tests | schema-resolution tests, strict/public gates | DONE |
| R2 | `validate-chain` default path performs lifecycle semantics despite being documented as integrity-only/generic. | AV-09 | Contract confusion; users cannot cleanly separate hash-chain validation from strict lifecycle validation. | Run lifecycle semantics only when `require_lifecycle=True`, `verify-lifecycle`, or `validate-chain --strict-lifecycle` is used; update docs/tests. | `sclite/integrity/chain.py`, `README.md`, `SPEC.md`, `docs/ARTIFACTS.md`, tests | integrity-chain tests, CLI JSON smoke, secure-bundle tests | DONE |
| R3 | Named GovEngine integration surface test is too shallow even though other gates cover the fixture. | AV-11 | A reader can mistake callable import coverage for semantic fixture compatibility. | Add fixture-level API and CLI smokes to the integration surface test. | `tests/test_govengine_integration_surface.py` | focused integration tests, public gate | DONE |
| R4 | GovEngine integration contract wording still centers the downstream `0.8.x` range without explaining SCLite `1.0.0` compatibility and non-widened downstream dependency state. | AV-13 | Public readers may confuse stable SCLite publication with an automatic downstream package sync. | Clarify source-compatible `1.0.x` surface and state that downstream widening is a separate GovEngine/Ravenclaw release decision. | `docs/GOVENGINE_INTEGRATION_CONTRACT.md` | public truth validator | DONE |
| R5 | Repository gate scripts assume a `python` executable, which is absent in the current local environment. | `scripts/public_validation_gate.sh` failed with `python: command not found`; `python3` and `.venv/bin/python` exist. | Developer gates can fail before exercising repository logic. | Resolve interpreter from `PYTHON`, local `.venv/bin/python`, `python`, then `python3`; make Makefile use the same preference. | `scripts/*.sh`, `Makefile` | gate scripts and full dev gate | DONE |
| R6 | `kernel_guard_hmac_v1.schema.json` was packaged but absent from `SCHEMA_FILES`; old root/repo schema fallback masked this registry gap. | Security regression failed after R1 with `not a packaged SCLite schema` for `schemas/kernel_guard_hmac_v1.schema.json`. | Guard verification would fail under the hardened resolver unless the schema is explicitly registered. | Add the Kernel Guard schema to `SCHEMA_FILES`; test registry coverage against packaged schemas. | `sclite/artifacts.py`, `tests/test_schema_resolution.py` | security regression gate | DONE |

## Non-Fix Decisions

- No version or release metadata change was needed: `pyproject.toml`,
  `sclite.__version__`, current docs, and `validate_public_truth.py` already
  agree on `1.0.0`.
- No CI command repair was needed: the current workflow uses `checkout@v6`,
  `setup-python@v6`, public/strict/security gates, pytest, and package dry-run.
- No PyPI release is required for this branch unless the owner decides to ship
  the behavior/security hardening as a patch release after review.
