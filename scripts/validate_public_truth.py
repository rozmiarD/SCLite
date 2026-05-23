#!/usr/bin/env python3
from __future__ import annotations

import importlib
import re
import sys
import tomllib
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import sclite  # noqa: E402
from sclite.bundles import review_bundle  # noqa: E402
from sclite.surfaces import build_public_validation_surface_index  # noqa: E402


EXPECTED_VERSION = '0.6.0a0'
EXPECTED_RELEASE_LABEL = '0.6.0-alpha'
EXPECTED_DISTRIBUTION = 'sclite-core'
EXPECTED_IMPORT_PACKAGE = 'sclite'
EXPECTED_GOVENGINE_RANGE = 'sclite-core>=0.6.0a0,<0.7'
PUBLIC_DOCS = (
    'README.md',
    'PUBLIC_STATUS.md',
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
    'sclite.bundles:validate_review_bundle_shape',
    'sclite.profiles:validate_trust_profile_ref',
    'sclite.profiles:validate_carrier_profile_ref',
    'sclite.scope_fidelity:build_lifecycle_scope_fidelity_report',
)
REQUIRED_FIXTURES = (
    'examples/review-bundle',
    'examples/govengine-integration',
    'examples/local-admin-change',
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
    _require(errors, 'README.md', readme, f'package-sclite--core%20{version}-blueviolet.svg')
    _require(errors, 'README.md', readme, f'https://pypi.org/project/sclite-core/{version}/')
    _require(errors, 'README.md', readme, f'python -m pip install sclite-core=={version}')


def _assert_current_claim_docs(errors: list[str], *, version: str, spec: str, artifact_docs: str) -> None:
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
    _require(errors, 'SPEC.md', spec, f'Current package release is `sclite-core=={version}`')
    _require(errors, 'SPEC.md', spec, 'The current front door is the review lifecycle substrate')
    _require(errors, 'SPEC.md', spec, 'v0.1 proof-trace artifacts remain only')
    _require(errors, 'SPEC.md', spec, 'Ravenclaw/public-proof migration')
    _require(errors, 'docs/ARTIFACTS.md', artifact_docs, f'Current public package line: `sclite-core=={version}`')
    _require(errors, 'docs/ARTIFACTS.md', artifact_docs, 'current integration front door is the review lifecycle')
    _require(errors, 'docs/ARTIFACTS.md', artifact_docs, 'Legacy v0.1 artifacts are compatibility/history material for Ravenclaw')


def _stable_import_errors() -> list[str]:
    errors: list[str] = []
    for spec in STABLE_IMPORTS:
        module_name, attr = spec.split(':', 1)
        module = importlib.import_module(module_name)
        if not callable(getattr(module, attr, None)):
            errors.append(f'stable_import_not_callable:{spec}')
    return errors


def _surface_fixture_errors() -> list[str]:
    errors: list[str] = []
    index = build_public_validation_surface_index(generated_at='2026-05-21T00:00:00+00:00')
    surface_paths = {str(surface.get('path') or '') for surface in index.get('surfaces') or []}
    for fixture in REQUIRED_FIXTURES:
        if fixture not in surface_paths:
            errors.append(f'public_surface_index_missing_fixture:{fixture}')
        try:
            record = review_bundle(ROOT / fixture, generated_at='2026-05-21T00:00:00+00:00')
        except Exception as exc:  # pragma: no cover - failure path reports details
            errors.append(f'{fixture}:review_bundle_failed:{exc}')
            continue
        if str(record.get('verdict')) != 'pass' and fixture != 'examples/review-bundle':
            errors.append(f'{fixture}:unexpected_review_verdict:{record.get("verdict")}')
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
    _assert_current_claim_docs(errors, version=version, spec=spec, artifact_docs=artifact_docs)
    _require(errors, 'README.md', readme, f'Version: `{version}`')
    _require(errors, 'README.md', readme, '0.6 alpha')
    _require(errors, 'PUBLIC_STATUS.md', public_status, f'Current package version: `{version}`.')
    _require(errors, 'PUBLIC_STATUS.md', public_status, f'Public release label: `{EXPECTED_RELEASE_LABEL}`.')
    _require(errors, 'PUBLIC_STATUS.md', public_status, f'PyPI publication: `{EXPECTED_DISTRIBUTION}=={version}` is the current alpha package line.')
    _require(errors, 'ROADMAP.md', roadmap, f'Current public package: `{EXPECTED_DISTRIBUTION}=={version}`')
    _require(errors, 'VALIDATION.md', validation, 'python scripts/validate_public_truth.py')
    _require(errors, 'PUBLICATION_CHECKLIST.md', publication, 'python scripts/validate_public_truth.py')
    _require(errors, 'CHANGELOG.md', changelog, f'## {EXPECTED_RELEASE_LABEL} - Multi-runtime proof substrate')
    _require(errors, 'docs/GOVENGINE_INTEGRATION_CONTRACT.md', integration_contract, EXPECTED_GOVENGINE_RANGE)
    _require(errors, 'docs/INTEGRATION_GUIDE.md', integration_guide, EXPECTED_GOVENGINE_RANGE)
    _require(errors, 'README.md', readme, 'Runtime dependencies are intentionally empty.')
    _require(errors, 'README.md', readme, f'Python import package remains `{EXPECTED_IMPORT_PACKAGE}`')
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
    errors.extend(_surface_fixture_errors())
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
