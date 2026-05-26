#!/usr/bin/env python3
from __future__ import annotations

import importlib
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import sclite  # noqa: E402
from sclite.bundles import review_bundle  # noqa: E402
from sclite.surfaces import build_public_validation_surface_index  # noqa: E402


EXPECTED_VERSION = '0.8.0b2'
EXPECTED_RELEASE_LABEL = '0.8.0-beta'
LATEST_PUBLISHED_VERSION = EXPECTED_VERSION
LATEST_PUBLISHED_LABEL = EXPECTED_RELEASE_LABEL
EXPECTED_DISTRIBUTION = 'sclite-core'
EXPECTED_IMPORT_PACKAGE = 'sclite'
EXPECTED_GOVENGINE_RANGE = 'sclite-core>=0.8.0b2,<0.9'
PUBLIC_DOCS = (
    'README.md',
    'PUBLIC_STATUS.md',
    'SECURITY.md',
    'CONTRIBUTING.md',
    'ROADMAP.md',
    'VALIDATION.md',
    'PUBLICATION_CHECKLIST.md',
    'SPEC.md',
    'docs/ARTIFACTS.md',
    'docs/GOVENGINE_INTEGRATION_CONTRACT.md',
    'docs/INTEGRATION_GUIDE.md',
    'docs/SCLITE_0_5_FREEZE.md',
)
STABLE_IMPORTS = (
    'sclite.integrity:artifact_descriptor',
    'sclite.integrity:verify_artifact_chain_manifest',
    'sclite.tickets:validate_ticket_semantics',
    'sclite.tickets:verify_ticket_use',
    'sclite.review:build_review_record_from_manifest',
    'sclite.bundles:review_bundle',
    'sclite.bundles:materialize_review_bundle',
    'sclite.bundles:validate_review_bundle_shape',
    'sclite.profiles:validate_trust_profile_ref',
    'sclite.profiles:validate_carrier_profile_ref',
    'sclite.scope_fidelity:build_lifecycle_scope_fidelity_report',
    'sclite.secure:verify_secure_bundle',
)
REQUIRED_FIXTURES = (
    'examples/lifecycle-review/review_record.json',
    'examples/review-bundle',
    'examples/govengine-integration',
    'examples/local-admin-change',
)
RETIRED_CURRENT_SURFACE_PATHS = (
    'examples/security-contract-proof',
    'examples/prepared-execution-spec/prepared_execution_spec.json',
    'examples/scope-fidelity-report/scope_fidelity_report.json',
)
FORBIDDEN_OVERCLAIMS = (
    'production-ready',
    'runtime execution is included',
    'executes tools',
    'implements OpenClaw',
    'implements MCP',
    'implements A2A',
    'PKI trust authority',
    'KMS support',
    'key-store support',
    'proves legal authorization',
)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def _pyproject() -> dict:
    return tomllib.loads(_read('pyproject.toml'))['project']


def _require(errors: list[str], path: str, text: str, expected: str) -> None:
    if expected not in text:
        errors.append(f'{path}:missing:{expected}')


def _assert_readme_package_truth(errors: list[str], readme: str, version: str) -> None:
    forbidden = (
        'img.shields.io/pypi/v/sclite-core',
        'label=package%3A%20sclite-core',
        'pip install sclite-core\n',
    )
    for marker in forbidden:
        if marker in readme:
            errors.append(f'README.md:prerelease_unsafe_package_claim:{marker}')
    if version != LATEST_PUBLISHED_VERSION:
        candidate_public_markers = (
            f'https://pypi.org/project/sclite-core/{version}/',
            f'python -m pip install sclite-core=={version}',
        )
        for marker in candidate_public_markers:
            if marker in readme:
                errors.append(f'README.md:unpublished_candidate_install_claim:{marker}')
    _require(errors, 'README.md', readme, f'Version: `{version}`')
    _require(errors, 'README.md', readme, f'package-sclite--core%20{LATEST_PUBLISHED_VERSION}-blueviolet.svg')
    _require(errors, 'README.md', readme, f'https://pypi.org/project/sclite-core/{LATEST_PUBLISHED_VERSION}/')
    _require(errors, 'README.md', readme, f'python -m pip install sclite-core=={LATEST_PUBLISHED_VERSION}')


def _assert_unpublished_candidate_truth(errors: list[str], paths: Mapping[str, str], version: str) -> None:
    if version == LATEST_PUBLISHED_VERSION:
        return
    forbidden_claims = (
        f'PyPI package: `{EXPECTED_DISTRIBUTION}=={version}`',
        f'Latest published PyPI package: `{EXPECTED_DISTRIBUTION}=={version}`',
        f'Published the beta package as `{EXPECTED_DISTRIBUTION}=={version}`',
    )
    for path, text in paths.items():
        for claim in forbidden_claims:
            if claim in text:
                errors.append(f'{path}:unpublished_candidate_claimed_published:{claim}')


def _assert_current_claim_docs(
    errors: list[str],
    *,
    version: str,
    readme: str,
    roadmap: str,
    spec: str,
    artifact_docs: str,
    integration_guide: str,
) -> None:
    stale_current_markers = (
        'Current package release is `sclite-core==0.5.1`',
        'Current package: `sclite-core==0.5.1`',
        'current public package: `sclite-core==0.5.1`',
    )
    for marker in stale_current_markers:
        if marker in spec:
            errors.append(f'SPEC.md:stale_current_package_claim:{marker}')
        if marker in artifact_docs:
            errors.append(f'docs/ARTIFACTS.md:stale_current_package_claim:{marker}')
    _require(errors, 'SPEC.md', spec, f'Current package is `sclite-core=={version}`')
    _require(errors, 'SPEC.md', spec, 'The current front door is the review lifecycle substrate')
    _require(errors, 'SPEC.md', spec, 'superseded proof-trace product path is retired')
    _require(errors, 'SPEC.md', spec, 'after Ravenclaw migrated to the')
    _require(errors, 'SPEC.md', spec, 'current lifecycle/review-bundle front door')
    _require(errors, 'README.md', readme, 'v0.8 beta surface freeze')
    _require(errors, 'README.md', readme, 'Published current beta line')
    _require(errors, 'ROADMAP.md', roadmap, '## 0.5.1 — GovEngine integration readiness\n\nStatus: published predecessor patch line.')
    _require(errors, 'docs/ARTIFACTS.md', artifact_docs, f'Current package: `sclite-core=={version}`')
    _require(errors, 'docs/ARTIFACTS.md', artifact_docs, f'latest published public package: `sclite-core=={LATEST_PUBLISHED_VERSION}`')
    _require(errors, 'docs/ARTIFACTS.md', artifact_docs, 'current integration front door is the review lifecycle')
    _require(errors, 'docs/ARTIFACTS.md', artifact_docs, 'superseded proof-trace product path is retired')
    _require(errors, 'docs/INTEGRATION_GUIDE.md', integration_guide, 'The current 0.8 beta')
    if 'The current 0.6 alpha line' in integration_guide:
        errors.append('docs/INTEGRATION_GUIDE.md:stale_current_alpha_line:0.6')


def _assert_roadmap_release_truth(errors: list[str], roadmap: str) -> None:
    stale_markers = (
        'Status: current alpha line implemented for validation and downstream migration.',
        'Delivered in the current candidate:',
        'Status: current alpha candidate implemented after Ravenclaw consumer migration.',
        'gates pass against the 0.8 candidate.',
    )
    for marker in stale_markers:
        if marker in roadmap:
            errors.append(f'ROADMAP.md:stale_published_candidate_claim:{marker}')
    _require(errors, 'ROADMAP.md', roadmap, 'Status: published predecessor migration line.')
    _require(errors, 'ROADMAP.md', roadmap, 'Delivered in `0.7.0-alpha`:')
    _require(errors, 'ROADMAP.md', roadmap, 'Status: published current alpha line after Ravenclaw consumer migration.')
    _require(errors, 'ROADMAP.md', roadmap, 'gates passed for the published `0.8.0-alpha` line.')
    _require(errors, 'ROADMAP.md', roadmap, '## 0.8.0-beta — Freeze lifecycle/review public responsibility')
    _require(errors, 'ROADMAP.md', roadmap, 'Status: published current beta line.')


def _stable_import_errors() -> list[str]:
    errors: list[str] = []
    for spec in STABLE_IMPORTS:
        module_name, attr = spec.split(':', 1)
        module = importlib.import_module(module_name)
        if not callable(getattr(module, attr, None)):
            errors.append(f'stable_import_not_callable:{spec}')
    return errors


def _curated_root_export_errors() -> list[str]:
    errors: list[str] = []
    required = ('materialize_review_bundle', 'review_bundle', 'verify_ticket_use')
    forbidden_legacy = (
        'PROOF_TRACE_FILES',
        'build_proof_trace_artifacts',
        'validate_public_proof_trace_artifacts',
        'build_evidence_bundle_artifact',
    )
    for name in required:
        if name not in sclite.__all__:
            errors.append(f'root_api_missing_current_export:{name}')
    for name in forbidden_legacy:
        if name in sclite.__all__:
            errors.append(f'root_api_exports_legacy_surface:{name}')
    return errors


def _surface_fixture_errors() -> list[str]:
    errors: list[str] = []
    index = build_public_validation_surface_index(generated_at='2026-05-21T00:00:00+00:00')
    surface_paths = {str(surface.get('path') or '') for surface in index.get('surfaces') or []}
    for fixture in REQUIRED_FIXTURES:
        if fixture not in surface_paths:
            errors.append(f'public_surface_index_missing_fixture:{fixture}')
        if not (ROOT / fixture).is_dir():
            continue
        try:
            record = review_bundle(ROOT / fixture, generated_at='2026-05-21T00:00:00+00:00')
        except Exception as exc:  # pragma: no cover - failure path reports details
            errors.append(f'{fixture}:review_bundle_failed:{exc}')
            continue
        if str(record.get('verdict')) != 'pass' and fixture != 'examples/review-bundle':
            errors.append(f'{fixture}:unexpected_review_verdict:{record.get("verdict")}')
    for path in RETIRED_CURRENT_SURFACE_PATHS:
        if path in surface_paths:
            errors.append(f'public_surface_index_advertises_legacy_fixture:{path}')
    return errors


def _snapshot_fixture_errors() -> list[str]:
    errors: list[str] = []
    path = 'examples/public-snapshot-manifest/public_snapshot_manifest.json'
    manifest = json.loads(_read(path))
    paths = {str(item.get('path') or '') for item in manifest.get('files') or []}
    if not paths:
        errors.append(f'{path}:missing_snapshot_files')
    if any(item.startswith('examples/security-contract-proof/') for item in paths):
        errors.append(f'{path}:advertises_legacy_proof_trace_as_current_snapshot')
    if not any(item.startswith('examples/review-bundle/') for item in paths):
        errors.append(f'{path}:missing_current_review_bundle_artifacts')
    return errors


def _retired_product_errors() -> list[str]:
    errors: list[str] = []
    removed_paths = (
        'sclite/validation.py',
        'examples/security-contract-proof',
        'sclite/examples/security-contract-proof',
        'examples/prepared-execution-spec',
        'sclite/examples/prepared-execution-spec',
    )
    removed_schemas = (
        'policy_decision.v0.1.schema.json',
        'prepared_execution_spec.v0.1.schema.json',
        'redacted_prepared_execution_spec.v0.1.schema.json',
        'approved_execution_spec.v0.1.schema.json',
        'execution_receipt.v0.1.schema.json',
        'evidence_bundle.v0.1.schema.json',
        'security_contract_validation_receipt.v0.1.schema.json',
    )
    for path in removed_paths:
        candidate = ROOT / path
        if candidate.is_file() or (candidate.is_dir() and any(item.is_file() for item in candidate.rglob('*'))):
            errors.append(f'retired_product_path_present:{path}')
    for schema in removed_schemas:
        if (ROOT / 'schemas' / schema).exists() or (ROOT / 'sclite' / 'schemas' / schema).exists():
            errors.append(f'retired_product_schema_present:{schema}')
    cli_text = _read('sclite/cli.py')
    for marker in ("add_parser('validate'", "add_parser('validation-receipt'"):
        if marker in cli_text:
            errors.append(f'retired_product_cli_present:{marker}')
    errors.extend(_retired_reference_errors({
        'examples/scope-fidelity-report/scope_fidelity_report.json':
            _read('examples/scope-fidelity-report/scope_fidelity_report.json'),
        'sclite/examples/scope-fidelity-report/scope_fidelity_report.json':
            _read('sclite/examples/scope-fidelity-report/scope_fidelity_report.json'),
    }))
    return errors


def _retired_reference_errors(text_by_path: Mapping[str, str]) -> list[str]:
    errors: list[str] = []
    for path, text in text_by_path.items():
        if 'examples/security-contract-proof/' in text or 'examples/prepared-execution-spec/' in text:
            errors.append(f'{path}:references_retired_product_path')
    return errors


def _documentation_drift_errors(text_by_path: Mapping[str, str]) -> list[str]:
    errors: list[str] = []
    forbidden_current_wording = (
        'prepared execution/ticket target',
        'published v0.3 scoped-ticket artifact',
    )
    for path, text in text_by_path.items():
        for wording in forbidden_current_wording:
            if wording in text:
                errors.append(f'{path}:stale_current_wording:{wording}')
    return errors


def _forbidden_claim_errors(paths: Iterable[str]) -> list[str]:
    errors: list[str] = []
    negation_markers = (
        'not ',
        'does not ',
        'do not ',
        'does_not_',
        'does-not-',
        'no ',
        'without ',
        'must not ',
        'must never ',
    )
    for path in paths:
        lines = _read(path).splitlines()
        for claim in FORBIDDEN_OVERCLAIMS:
            claim_text = claim.lower()
            for line_number, line in enumerate(lines, 1):
                lowered = line.lower()
                if claim_text not in lowered:
                    continue
                context = '\n'.join(lines[max(0, line_number - 6):line_number]).lower()
                if 'do not claim' in context or 'does not claim' in context:
                    continue
                before_claim = lowered[:lowered.index(claim_text)]
                if any(marker in before_claim for marker in negation_markers):
                    continue
                errors.append(f'{path}:{line_number}:forbidden_overclaim:{claim}')
    return errors


def collect_errors() -> list[str]:
    errors: list[str] = []
    project = _pyproject()
    version = str(project['version'])
    readme = _read('README.md')
    public_status = _read('PUBLIC_STATUS.md')
    roadmap = _read('ROADMAP.md')
    validation = _read('VALIDATION.md')
    publication = _read('PUBLICATION_CHECKLIST.md')
    spec = _read('SPEC.md')
    artifact_docs = _read('docs/ARTIFACTS.md')
    changelog = _read('CHANGELOG.md')
    integration_contract = _read('docs/GOVENGINE_INTEGRATION_CONTRACT.md')
    integration_guide = _read('docs/INTEGRATION_GUIDE.md')
    workflow = _read('.github/workflows/ci.yml')

    if project['name'] != EXPECTED_DISTRIBUTION:
        errors.append(f'distribution_name_mismatch:{project["name"]}')
    if version != EXPECTED_VERSION:
        errors.append(f'pyproject_version_mismatch:{version}!={EXPECTED_VERSION}')
    if sclite.__version__ != version:
        errors.append(f'package_version_mismatch:{sclite.__version__}!={version}')
    if project.get('dependencies') != []:
        errors.append(f'runtime_dependencies_not_empty:{project.get("dependencies")}')

    _assert_readme_package_truth(errors, readme, version)
    _assert_current_claim_docs(
        errors,
        version=version,
        readme=readme,
        roadmap=roadmap,
        spec=spec,
        artifact_docs=artifact_docs,
        integration_guide=integration_guide,
    )
    _assert_roadmap_release_truth(errors, roadmap)
    _require(errors, 'README.md', readme, f'Version: `{version}`')
    _require(errors, 'README.md', readme, 'published 0.8 beta')
    _require(errors, 'PUBLIC_STATUS.md', public_status, f'Current release version: `{version}`.')
    _require(errors, 'PUBLIC_STATUS.md', public_status, f'Release label: `{EXPECTED_RELEASE_LABEL}`.')
    _require(errors, 'PUBLIC_STATUS.md', public_status, f'Latest published PyPI package: `{EXPECTED_DISTRIBUTION}=={LATEST_PUBLISHED_VERSION}` (`{LATEST_PUBLISHED_LABEL}`).')
    _require(errors, 'ROADMAP.md', roadmap, f'Current package: `{EXPECTED_DISTRIBUTION}=={version}`')
    _require(errors, 'ROADMAP.md', roadmap, f'Latest published public package: `{EXPECTED_DISTRIBUTION}=={LATEST_PUBLISHED_VERSION}`')
    _require(errors, 'VALIDATION.md', validation, 'python scripts/validate_public_truth.py')
    _require(errors, 'PUBLICATION_CHECKLIST.md', publication, 'python scripts/validate_public_truth.py')
    _require(errors, 'CHANGELOG.md', changelog, f'## {EXPECTED_RELEASE_LABEL} - Lifecycle/review surface freeze')
    _require(errors, 'CHANGELOG.md', changelog, f'published `{EXPECTED_DISTRIBUTION}=={LATEST_PUBLISHED_VERSION}` package line')
    _require(errors, 'docs/GOVENGINE_INTEGRATION_CONTRACT.md', integration_contract, EXPECTED_GOVENGINE_RANGE)
    _require(errors, 'docs/INTEGRATION_GUIDE.md', integration_guide, EXPECTED_GOVENGINE_RANGE)
    _require(errors, 'README.md', readme, 'Runtime dependencies are intentionally empty.')
    _require(errors, 'README.md', readme, f'Python import package remains `{EXPECTED_IMPORT_PACKAGE}`')
    _require(errors, 'CONTRIBUTING.md', _read('CONTRIBUTING.md'), 'define / validate / hash / bind / redact / review / verify')
    _require(errors, 'SPEC.md', spec, 'define / validate / hash / bind / redact / review / verify')
    _require(errors, 'SECURITY.md', _read('SECURITY.md'), f'current published beta package is `{EXPECTED_DISTRIBUTION}=={EXPECTED_VERSION}`')
    _require(errors, '.github/workflows/ci.yml', workflow, 'actions/checkout@v6')
    _require(errors, '.github/workflows/ci.yml', workflow, 'actions/setup-python@v6')
    _require(errors, '.github/workflows/ci.yml', workflow, "python-version: ['3.11', '3.12', '3.13']")
    _require(errors, '.github/workflows/ci.yml', workflow, 'scripts/public_validation_gate.sh')
    _require(errors, '.github/workflows/ci.yml', workflow, 'scripts/strict_schema_gate.sh')
    _require(errors, '.github/workflows/ci.yml', workflow, 'package-dry-run:')
    _require(errors, '.github/workflows/ci.yml', workflow, 'rm -rf dist build *.egg-info')
    _require(errors, '.github/workflows/ci.yml', workflow, 'python -m twine check dist/*')
    _require(errors, '.github/workflows/ci.yml', workflow, 'python -m pip check')

    errors.extend(_stable_import_errors())
    errors.extend(_curated_root_export_errors())
    errors.extend(_surface_fixture_errors())
    errors.extend(_snapshot_fixture_errors())
    errors.extend(_retired_product_errors())
    errors.extend(_documentation_drift_errors({
        'examples/bad-review-bundle-cross-host/README.md':
            _read('examples/bad-review-bundle-cross-host/README.md'),
        'sclite/examples/bad-review-bundle-cross-host/README.md':
            _read('sclite/examples/bad-review-bundle-cross-host/README.md'),
        'examples/trust-carrier-profiles/README.md':
            _read('examples/trust-carrier-profiles/README.md'),
        'sclite/examples/trust-carrier-profiles/README.md':
            _read('sclite/examples/trust-carrier-profiles/README.md'),
    }))
    errors.extend(_forbidden_claim_errors(PUBLIC_DOCS))

    return errors


def main() -> int:
    errors = collect_errors()
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f'public_truth_ok:sclite-core=={EXPECTED_VERSION}:import=sclite:runtime_deps=0')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
