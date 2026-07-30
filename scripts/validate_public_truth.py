#!/usr/bin/env python3
from __future__ import annotations

import importlib
import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import sclite  # noqa: E402
from sclite._cli_impl import DEVTOOLS_COMMANDS, KERNEL_COMMANDS  # noqa: E402
from sclite.bundles import review_bundle  # noqa: E402
from sclite.consumer_contracts import validate_public_export_inventory  # noqa: E402
from sclite.surfaces import build_public_validation_surface_index  # noqa: E402


EXPECTED_VERSION = '2.0.1'
EXPECTED_RELEASE_LABEL = '2.0.1'
LATEST_PUBLISHED_VERSION = '2.0.1'
LATEST_PUBLISHED_LABEL = '2.0.1'
EXPECTED_DISTRIBUTION = 'sclite-core'
EXPECTED_IMPORT_PACKAGE = 'sclite'
PYPI_LONG_DESCRIPTION_PATH = 'PYPI_LONG_DESCRIPTION.md'
PYPI_LONG_DESCRIPTION_SHA256 = '737ac8a33c8563136818bd14f2e13ac4dea7aa64fa351a508f95f632e61c3656'
EXPECTED_SOURCE_STATUS = 'published stable non-prerelease 2.0.1 release'
STABLE_IMPORTS = (
    'sclite.integrity:artifact_descriptor',
    'sclite.integrity:verify_artifact_chain_manifest',
    'sclite.integrity:verify_lifecycle_manifest',
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
    'sclite.secure:verify_secure_bundle_result',
    'sclite.verification_result:serialize_verification_result',
    'sclite.testing:build_guarded_strict_verification_result_fixture',
    'sclite.disclosure:build_disclosure_status',
    'sclite.disclosure:validate_disclosure_transition',
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
    _require(
        errors,
        'README.md',
        readme,
        f'[![Current source: sclite-core {version}]'
        f'(https://img.shields.io/badge/current%20source-sclite--core%20{version}-blueviolet.svg)',
    )
    _require(errors, 'README.md', readme, f'Release status: **{EXPECTED_SOURCE_STATUS}**')
    _require(errors, 'README.md', readme, f'package-sclite--core%20{LATEST_PUBLISHED_VERSION}-blueviolet.svg')
    _require(errors, 'README.md', readme, f'https://pypi.org/project/sclite-core/{LATEST_PUBLISHED_VERSION}/')
    _require(errors, 'README.md', readme, f'python -m pip install sclite-core=={LATEST_PUBLISHED_VERSION}')


def _assert_current_publication_truth(errors: list[str], paths: Mapping[str, str]) -> None:
    current_version = rf'(?<![\d.]){re.escape(EXPECTED_VERSION)}(?![\d.])'
    current_unpublished = re.compile(
        rf'(?:{current_version}[^\n]{{0,100}}\b(?:unpublished|has not(?: yet)? been '
        r'published|is not(?: yet)? (?:published|available|installable|released))\b|'
        rf'\b(?:unpublished|has not(?: yet)? been published|is not(?: yet)? '
        rf'(?:published|available|installable|released))\b[^\n]{{0,100}}{current_version})',
        re.I,
    )
    publication_pending = re.compile(r'\bpublication(?: is| remains)? pending\b', re.I)
    explicit_semver = re.compile(r'(?<![\d.])\d+\.\d+\.\d+(?![\d.])')
    source_semver = re.compile(
        r'\b(?:current\s+)?source(?:\s+(?:package|version))?\b[^\n]{0,60}?'
        r'(?P<version>(?<![\d.])\d+\.\d+\.\d+(?![\d.]))',
        re.I,
    )
    latest_published_expected = re.compile(
        rf'\blatest\s+published\s+(?:(?:PyPI|public)\s+)?package\b[^\n]{{0,60}}'
        rf'`?{re.escape(EXPECTED_DISTRIBUTION)}=={re.escape(EXPECTED_VERSION)}`?',
        re.I,
    )
    stale_published_package = re.compile(
        r'\b(?:latest published (?:(?:PyPI|public) )?package|'
        r'current published stable package)\b\s*(?::|is|remains)?\s*'
        r'`?sclite-core==2\.0\.0`?',
        re.I,
    )
    stale_published_release = re.compile(
        r'(?:`?sclite-core==2\.0\.0`?|\bSCLite\s+2\.0\.0\b|\b2\.0\.0\b)'
        r'\s+(?:is|remains)\s+(?:the\s+)?(?:latest|current) published stable '
        r'(?:package|release)\b',
        re.I,
    )
    for path, text in paths.items():
        for line_number, line in enumerate(text.splitlines(), start=1):
            line_versions = set(explicit_semver.findall(line))
            future_version_guidance = bool(
                re.search(r'\bfuture\b', line, re.I)
                and line_versions - {EXPECTED_VERSION}
                and EXPECTED_VERSION not in line_versions
            )
            future_source_split = bool(latest_published_expected.search(line)) and any(
                match.group('version') != EXPECTED_VERSION
                for match in source_semver.finditer(line)
            )
            if current_unpublished.search(line):
                marker = 'current_2_0_1_unpublished'
            elif publication_pending.search(line) and not (
                future_version_guidance or future_source_split
            ):
                marker = 'publication_pending'
            elif stale_published_package.search(line) or stale_published_release.search(line):
                marker = 'stale_published_2_0_0'
            else:
                continue
            errors.append(f'{path}:{line_number}:contradictory_current_publication_truth:{marker}')


def _assert_distribution_long_description_truth(
    errors: list[str], description: bytes, version: str
) -> None:
    del version
    actual = hashlib.sha256(description).hexdigest()
    if actual != PYPI_LONG_DESCRIPTION_SHA256:
        errors.append(
            f'{PYPI_LONG_DESCRIPTION_PATH}:sha256:{actual}!={PYPI_LONG_DESCRIPTION_SHA256}'
        )


def _assert_canonical_release_artifact_boundaries(
    errors: list[str], *, workflow: str, release_workflow: str, package_smoke: str, manifest: str
) -> None:
    def noncomment_lines(text: str) -> list[str]:
        return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith('#')]

    for path, text, expected, expected_count in (
        (
            '.github/workflows/ci.yml',
            workflow,
            'run: PYTHON=python bash scripts/build_release_artifacts.sh --outdir dist',
            1,
        ),
        (
            '.github/workflows/release.yml',
            release_workflow,
            'PYTHON=python bash scripts/build_release_artifacts.sh --outdir dist',
            2,
        ),
        (
            'scripts/package_smoke.sh',
            package_smoke,
            'PYTHON="${BUILD_PY}" bash scripts/build_release_artifacts.sh --outdir "${TMPDIR_ROOT}/dist"',
            1,
        ),
    ):
        actual_count = noncomment_lines(text).count(expected)
        if actual_count != expected_count:
            errors.append(f'{path}:canonical_release_helper_count:{actual_count}')
    for required in (
        'include scripts/build_release_artifacts.sh',
        'include scripts/validate_distribution_metadata.py',
    ):
        if noncomment_lines(manifest).count(required) != 1:
            errors.append(f'MANIFEST.in:missing:{required}')


def _assert_unpublished_candidate_truth(errors: list[str], paths: Mapping[str, str], version: str) -> None:
    if version == LATEST_PUBLISHED_VERSION:
        return
    candidate_pin = f'{EXPECTED_DISTRIBUTION}=={version}'
    candidate_url = f'https://pypi.org/project/{EXPECTED_DISTRIBUTION}/{version}/'
    candidate_badge_patterns = (
        re.compile(
            rf'!\[[^\]]*\b(?:PyPI|package)\b[^\]]*\b{re.escape(version)}\b[^\]]*\]'
            r'\([^)]*img\.shields\.io/',
            re.I,
        ),
        re.compile(
            rf'img\.shields\.io/badge/[^\s)]*(?:pypi|package)[^\s)]*{re.escape(version)}',
            re.I,
        ),
    )
    candidate_install = re.compile(
        rf'\bpip\s+install\b[^\n]{{0,120}}?[\'"`]?{re.escape(candidate_pin)}[\'"`]?',
        re.I,
    )
    candidate_version_text = rf'(?<![\d.]){re.escape(version)}(?![\d.])'
    candidate_version = re.compile(candidate_version_text, re.I)
    publication_context = re.compile(r'\b(?:sclite(?:-core)?|package|pypi|release)\b', re.I)
    explicit_candidate_negative = (
        re.compile(
            rf'{candidate_version_text}[^.;!?]{{0,80}}\b(?:has|have|is|was)\s+not\s+'
            r'(?:yet\s+)?(?:been\s+)?(?:published|released|available|installable)\b',
            re.I,
        ),
        re.compile(
            rf'{candidate_version_text}[^.;!?]{{0,80}}\bmust\s+not\b[^.;!?]{{0,80}}'
            r'\b(?:published|released|available|installable)\b',
            re.I,
        ),
        re.compile(
            rf'{candidate_version_text}[^.;!?]{{0,80}}\b(?:is|remains)\s+unpublished\b',
            re.I,
        ),
        re.compile(
            rf'{candidate_version_text}[^\n]{{0,120}}\bpublication\s+(?:is\s+)?pending\b',
            re.I,
        ),
    )
    current_source_candidate = re.compile(
        rf'\b(?:current\s+)?source(?:\s+(?:package|version))?\b'
        rf'[^\n]{{0,60}}(?:{re.escape(EXPECTED_DISTRIBUTION)}==)?'
        rf'{re.escape(version)}',
        re.I,
    )
    latest_published_other = re.compile(
        rf'\blatest\s+published\s+(?:(?:PyPI|public)\s+)?package\b'
        rf'[^\n]{{0,60}}(?:{re.escape(EXPECTED_DISTRIBUTION)}==)?'
        rf'{re.escape(LATEST_PUBLISHED_VERSION)}',
        re.I,
    )
    positive_before_candidate = re.compile(
        rf'\b(?:published|released|available)\b'
        rf'(?:(?!(?<![\d.])\d+\.\d+\.\d+(?![\d.]))[^;.!?]){{0,100}}'
        rf'{candidate_version_text}',
        re.I,
    )
    positive_after_candidate = re.compile(
        rf'{candidate_version_text}[^;.!?]{{0,60}}\b'
        r'(?:(?:is|was|became|has\s+been)\s+(?:now\s+)?|now\s+)'
        r'(?:published|released|available)\b',
        re.I,
    )

    for path, text in paths.items():
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not candidate_version.search(line) and version not in line:
                continue
            candidate_positive_claim = bool(
                publication_context.search(line)
                and (
                    positive_before_candidate.search(line)
                    or positive_after_candidate.search(line)
                )
            )
            if candidate_positive_claim:
                errors.append(
                    f'{path}:{line_number}:unpublished_candidate_claimed_published:'
                    f'{line.strip()}'
                )
                continue
            direct_distribution_claim = (
                candidate_url in line
                or candidate_install.search(line)
                or any(pattern.search(line) for pattern in candidate_badge_patterns)
            )
            if direct_distribution_claim:
                errors.append(
                    f'{path}:{line_number}:unpublished_candidate_distribution_claim:'
                    f'{line.strip()}'
                )
                continue
            explicitly_negative = any(
                pattern.search(line) for pattern in explicit_candidate_negative
            )
            proven_source_published_split = bool(
                current_source_candidate.search(line)
                and latest_published_other.search(line)
            )
            if re.search(r'\bPyPI\b', line, re.I):
                claimed_published = not (
                    explicitly_negative or proven_source_published_split
                )
            else:
                claimed_published = False
            if claimed_published:
                errors.append(
                    f'{path}:{line_number}:unpublished_candidate_claimed_published:'
                    f'{line.strip()}'
                )


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
    _require(errors, 'SPEC.md', spec, f'Current source package is `sclite-core=={version}`')
    _require(errors, 'SPEC.md', spec, 'The current front door is the review lifecycle substrate')
    _require(errors, 'SPEC.md', spec, 'superseded proof-trace product path is retired')
    _require(errors, 'SPEC.md', spec, 'after controlled consumers')
    _require(errors, 'SPEC.md', spec, 'current lifecycle/review-bundle front door')
    _require(errors, 'README.md', readme, EXPECTED_SOURCE_STATUS)
    _require(errors, 'README.md', readme, 'Development Status :: 4 - Beta')
    _require(errors, 'README.md', readme, '## Out of Scope')
    _require(errors, 'README.md', readme, 'Runtime execution: out of scope; owned by RExecOp or another host runtime')
    _require(errors, 'README.md', readme, 'GovEngine | governance, admission, policy decisions')
    _require(errors, 'README.md', readme, 'RExecOp | domain-neutral lifecycle runner')
    _require(errors, 'README.md', readme, 'When `--guard` is provided explicitly, SCLite resolves it relative to the')
    _require(errors, 'VALIDATION.md', _read('VALIDATION.md'), 'Explicit `--guard` paths are')
    _require(errors, 'ROADMAP.md', roadmap, 'SCLite 2.0 is the frozen truth')
    _require(errors, 'ROADMAP.md', roadmap, '## 2.0 maintenance policy')
    _require(errors, 'ROADMAP.md', roadmap, 'feature-freeze-compatible maintenance source')
    _require(errors, 'docs/ARTIFACTS.md', artifact_docs, f'Current source package: `sclite-core=={version}`')
    _require(errors, 'docs/ARTIFACTS.md', artifact_docs, 'latest published public package:')
    _require(errors, 'docs/ARTIFACTS.md', artifact_docs, 'current integration front door is the review lifecycle')
    _require(errors, 'docs/ARTIFACTS.md', artifact_docs, 'superseded proof-trace product path is also retired')
    _require(errors, 'docs/INTEGRATION_GUIDE.md', integration_guide, 'The current 2.0 stable release')
    if 'It is not an installed/current SCLite surface in the 0.8 beta release.' in readme:
        errors.append('README.md:stale_current_release_wording:0.8 beta release')
    if 'published 1.0 release candidate' in readme:
        errors.append('README.md:stale_current_release_wording:1.0 release candidate')
    if 'The current 0.6 alpha line' in integration_guide:
        errors.append('docs/INTEGRATION_GUIDE.md:stale_current_alpha_line:0.6')


def _assert_roadmap_release_truth(errors: list[str], roadmap: str) -> None:
    forbidden = (
        'Status: current alpha',
        'Status: published current stable release.',
        'Delivered in the current candidate:',
        'Candidate post-0.5 examples:',
    )
    for marker in forbidden:
        if marker in roadmap:
            errors.append(f'ROADMAP.md:historical_line_in_active_roadmap:{marker}')
    _require(errors, 'ROADMAP.md', roadmap, 'docs/archive/ROADMAP_VERSION_HISTORY.md')
    _require(errors, 'ROADMAP.md', roadmap, 'Documentation changes on `main` do not require a package release.')


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
    errors.extend(validate_public_export_inventory(sclite.__all__))
    required = (
        'materialize_review_bundle',
        'review_bundle',
        'verify_ticket_use',
        'verify_secure_bundle',
        'verify_secure_bundle_result',
        'serialize_verification_result',
        'build_disclosure_status',
        'validate_disclosure_transition',
        'build_kernel_guard_manifest',
    )
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
    api_doc = _read('docs/PUBLIC_API.md')
    for name in sclite.__all__:
        if f'`{name}`' not in api_doc:
            errors.append(f'public_api_doc_missing_export:{name}')
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
    cli_text = _read('sclite/_cli_impl.py')
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


def _markdown_paths(*, include_archive: bool) -> tuple[str, ...]:
    paths: set[str] = set()
    ignored_parts = {'.git', '.venv', '.pytest_cache', 'build', 'dist'}
    for path in ROOT.rglob('*.md'):
        if not path.is_file():
            continue
        relative_path = path.relative_to(ROOT)
        if any(
            part in ignored_parts or part.endswith('.egg-info')
            for part in relative_path.parts
        ):
            continue
        relative = relative_path.as_posix()
        if relative == 'CHANGELOG.md':
            continue
        if not include_archive and relative.startswith('docs/archive/'):
            continue
        paths.add(relative)
    return tuple(sorted(paths))


def _documentation_command_errors(paths: Iterable[str]) -> list[str]:
    errors: list[str] = []
    direct = re.compile(r'(?<![\w.-])(sclite-devtools|sclite|scl)\s+([a-z][a-z0-9-]*)')
    module = re.compile(
        r'python(?:3)?\s+-m\s+sclite\.(devtools|kernel_cli)\s+([a-z][a-z0-9-]*)'
    )
    all_commands = KERNEL_COMMANDS | DEVTOOLS_COMMANDS

    def check(
        path: str,
        line_number: int,
        line: str,
        command_start: int,
        entrypoint: str,
        command: str,
    ) -> None:
        if command not in all_commands:
            if command in {'validate', 'validation-receipt'}:
                errors.append(
                    f'{path}:{line_number}:documentation_retired_cli_command:{command}'
                )
            elif not line[:command_start].strip():
                errors.append(
                    f'{path}:{line_number}:documentation_unknown_cli_command:{command}'
                )
            return
        expected = 'sclite-devtools' if command in DEVTOOLS_COMMANDS else 'sclite'
        actual = 'sclite-devtools' if entrypoint == 'devtools' else entrypoint
        if actual in {'scl', 'kernel_cli'}:
            actual = 'sclite'
        if actual != expected:
            errors.append(
                f'{path}:{line_number}:documentation_cli_owner_mismatch:'
                f'{command}:{actual}!={expected}'
            )

    for path in paths:
        for line_number, line in enumerate(_read(path).splitlines(), 1):
            module_spans: list[tuple[int, int]] = []
            for match in module.finditer(line):
                module_spans.append(match.span())
                check(
                    path,
                    line_number,
                    line,
                    match.start(),
                    match.group(1),
                    match.group(2),
                )
            for match in direct.finditer(line):
                if any(start <= match.start() < end for start, end in module_spans):
                    continue
                check(
                    path,
                    line_number,
                    line,
                    match.start(),
                    match.group(1),
                    match.group(2),
                )
    return errors


def _documentation_fixture_command_errors(paths: Iterable[str]) -> list[str]:
    errors: list[str] = []
    validate_artifact = re.compile(
        r'validate-artifact\s+--schema\s+([A-Za-z0-9_.-]+)\s+([A-Za-z0-9_./-]+\.json)'
    )
    for path in paths:
        normalized = _read(path).replace('\\\n', ' ')
        for schema_name, artifact_path in validate_artifact.findall(normalized):
            candidate = ROOT / artifact_path
            if not candidate.is_file():
                continue
            try:
                artifact = json.loads(candidate.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError):
                errors.append(
                    f'{path}:documentation_example_artifact_unreadable:{artifact_path}'
                )
                continue
            if not isinstance(artifact, Mapping):
                continue
            schema_ref = str(artifact.get('schema_ref') or '')
            if schema_ref:
                expected = schema_ref.removeprefix('schemas/').removesuffix('.schema.json')
            else:
                artifact_type = str(artifact.get('artifact_type') or '')
                schema_version = str(artifact.get('schema_version') or '')
                expected = f'{artifact_type}.{schema_version}' if artifact_type and schema_version else ''
            if expected and schema_name != expected:
                errors.append(
                    f'{path}:documentation_example_schema_mismatch:'
                    f'{artifact_path}:{schema_name}!={expected}'
                )
    return errors


def _documentation_invocation_errors(paths: Iterable[str]) -> list[str]:
    errors: list[str] = []
    legacy_consumer_flags = ('--govengine', '--rexecop', '--tecrax')
    for path in paths:
        normalized = _read(path).replace('\\\n', ' ')
        for line_number, line in enumerate(normalized.splitlines(), 1):
            if 'validate_forbidden_consumer_imports.py' in line:
                for flag in legacy_consumer_flags:
                    if re.search(rf'(?<!\S){re.escape(flag)}(?:\s|$)', line):
                        errors.append(
                            f'{path}:{line_number}:'
                            f'documentation_consumer_validator_unsupported_flag:{flag}'
                        )
            if (
                'export-review-bundle' in line
                and 'examples/govengine-integration' in line
                and not re.search(r'--mode(?:\s+|=)local_review(?:\s|$)', line)
            ):
                errors.append(
                    f'{path}:{line_number}:'
                    'documentation_govengine_export_requires_local_review'
                )
    return errors


def _documentation_reference_errors(paths: Iterable[str]) -> list[str]:
    errors: list[str] = []
    test_ref = re.compile(r'(?<![\w/])(tests/[A-Za-z0-9_./-]+\.py)')
    link = re.compile(r'!?\[[^\]]*\]\(([^)]+)\)')
    root = ROOT.resolve()

    for path in paths:
        text = _read(path)
        for reference in sorted(set(test_ref.findall(text))):
            if not (ROOT / reference).is_file():
                errors.append(f'{path}:documentation_missing_test_reference:{reference}')
        for line_number, line_text in enumerate(text.splitlines(), 1):
            for raw_target in link.findall(line_text):
                target = raw_target.strip().strip('<>')
                if (
                    not target
                    or target.startswith(('#', 'http://', 'https://', 'mailto:'))
                ):
                    continue
                target = target.split('#', 1)[0].strip()
                if not target:
                    continue
                candidate = ((ROOT / path).parent / target).resolve()
                if not candidate.is_relative_to(root) or not candidate.exists():
                    errors.append(
                        f'{path}:{line_number}:documentation_broken_local_link:{target}'
                    )
    return errors


def _current_document_wording_errors(text_by_path: Mapping[str, str]) -> list[str]:
    errors: list[str] = []
    stale_markers = (
        'for the 1.0 line',
        'for the 1.0 release line',
        'on the 1.0 stable line',
        'published `1.0.4` stable package line',
        '`1.0.0` installed/current surface',
    )
    removed_schema_names = (
        'observation_envelope.v0.1',
        'finding.v0.1',
        'reaction_plan.v0.1',
        'escalation_proposal.v0.1',
        'trigger_decision.v0.1',
        'watchdog_decision.v0.1',
        'automation_chain.v0.1',
    )
    removed_schema_allowed = {
        'docs/MIGRATING_TO_2.md',
        'docs/SCHEMA_COMPATIBILITY.md',
    }
    for path, text in text_by_path.items():
        for marker in stale_markers:
            if marker in text:
                errors.append(f'{path}:stale_current_release_wording:{marker}')
        if path in removed_schema_allowed:
            continue
        for schema_name in removed_schema_names:
            if schema_name in text:
                errors.append(
                    f'{path}:removed_schema_advertised_in_current_docs:{schema_name}'
                )
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


def _workflow_executable_lines(workflow: str) -> list[str]:
    workflow = re.sub(r'\\\s*\n\s*', ' ', workflow)
    lines: list[str] = []
    for line in workflow.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        normalized = re.sub(r'\s+#.*$', '', ' '.join(line.strip().split()))
        if normalized.startswith('run: '):
            normalized = normalized.removeprefix('run: ')
        lines.append(normalized)
    return lines


def _assert_product_sbom_workflow(errors: list[str], *, path: str, workflow: str, output: str) -> None:
    lines = _workflow_executable_lines(workflow)
    target_venv = '"${TARGET_VENV}"'
    target_python = '"${TARGET_VENV}/bin/python"'
    target_creation = (
        'TARGET_VENV="$(mktemp -d "${RUNNER_TEMP}/sclite-product-sbom.XXXXXX")"'
    )
    install = (
        f'python -m pip --python {target_python} install --no-index --no-deps dist/*.whl'
    )
    generate = (
        f'cyclonedx-py environment {target_python} --pyproject pyproject.toml '
        f'--mc-type library --output-reproducible --output-file {output}'
    )
    validate = (
        f'python scripts/validate_product_sbom.py --wheel dist/*.whl --sbom {output}'
    )
    required_lines = (
        target_creation,
        f'python -m venv --without-pip {target_venv}',
        install,
        validate,
    )
    for required in required_lines:
        if required not in lines:
            errors.append(f'{path}:missing_product_sbom_command:{required}')

    product_step_count = lines.count('- name: Product SBOM')
    if product_step_count != 1:
        errors.append(f'{path}:product_sbom_step_count:{product_step_count}')
    cyclonedx_lines = [line for line in lines if line.startswith('cyclonedx-py ')]
    if cyclonedx_lines != [generate]:
        errors.append(f'{path}:product_sbom_cyclonedx_invocation_invalid')
    if any('Dependency audit and SBOM' in line for line in lines):
        errors.append(f'{path}:dependency_audit_and_product_sbom_must_be_distinct')
    if any(line.startswith('cyclonedx-py environment --output-file') for line in lines):
        errors.append(f'{path}:tool_environment_sbom_forbidden')

    def position(line: str) -> int:
        return lines.index(line) if line in lines else -1

    build_positions = [
        index for index, line in enumerate(lines)
        if 'scripts/build_release_artifacts.sh' in line
    ]
    target_position = position(target_creation)
    venv_position = position(f'python -m venv --without-pip {target_venv}')
    install_position = position(install)
    generate_position = position(generate)
    validate_position = position(validate)
    if not build_positions or max(build_positions) >= generate_position:
        errors.append(f'{path}:product_sbom_must_follow_wheel_build')
    if not (target_position < venv_position < install_position < generate_position < validate_position):
        errors.append(f'{path}:product_sbom_validation_must_follow_generation')


def collect_errors() -> list[str]:
    errors: list[str] = []
    project = _pyproject()
    version = str(project['version'])
    readme = _read('README.md')
    distribution_description = (ROOT / PYPI_LONG_DESCRIPTION_PATH).read_bytes()
    public_status = _read('PUBLIC_STATUS.md')
    roadmap = _read('ROADMAP.md')
    validation = _read('VALIDATION.md')
    publication = _read('PUBLICATION_CHECKLIST.md')
    spec = _read('SPEC.md')
    security_model = _read('SECURITY_MODEL.md')
    security_profiles = _read('docs/SECURITY_PROFILES.md')
    artifact_docs = _read('docs/ARTIFACTS.md')
    changelog = _read('CHANGELOG.md')
    integration_contract = _read('docs/GOVENGINE_INTEGRATION_CONTRACT.md')
    integration_guide = _read('docs/INTEGRATION_GUIDE.md')
    workflow = _read('.github/workflows/ci.yml')
    release_workflow = _read('.github/workflows/release.yml')
    package_smoke = _read('scripts/package_smoke.sh')
    manifest = _read('MANIFEST.in')
    active_markdown = _markdown_paths(include_archive=False)
    all_markdown = _markdown_paths(include_archive=True)

    if project['name'] != EXPECTED_DISTRIBUTION:
        errors.append(f'distribution_name_mismatch:{project["name"]}')
    if project.get('readme') != PYPI_LONG_DESCRIPTION_PATH:
        errors.append(
            f'project_readme_mismatch:{project.get("readme")}!={PYPI_LONG_DESCRIPTION_PATH}'
        )
    if version != EXPECTED_VERSION:
        errors.append(f'pyproject_version_mismatch:{version}!={EXPECTED_VERSION}')
    if sclite.__version__ != version:
        errors.append(f'package_version_mismatch:{sclite.__version__}!={version}')
    if project.get('dependencies') != []:
        errors.append(f'runtime_dependencies_not_empty:{project.get("dependencies")}')

    _assert_readme_package_truth(errors, readme, version)
    _assert_distribution_long_description_truth(errors, distribution_description, version)
    _assert_unpublished_candidate_truth(
        errors,
        {
            **{
                path: _read(path)
                for path in active_markdown
                if path != PYPI_LONG_DESCRIPTION_PATH
            },
            'CHANGELOG.md': changelog,
        },
        version,
    )
    _assert_current_publication_truth(errors, {
        'README.md': readme,
        'PUBLIC_STATUS.md': public_status,
        'ROADMAP.md': roadmap,
        'SPEC.md': spec,
        'SECURITY.md': _read('SECURITY.md'),
        'VALIDATION.md': validation,
        'PUBLICATION_CHECKLIST.md': publication,
        'docs/ARTIFACTS.md': artifact_docs,
        'docs/SCHEMA_COMPATIBILITY.md': _read('docs/SCHEMA_COMPATIBILITY.md'),
    })
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
    _require(errors, 'README.md', readme, EXPECTED_SOURCE_STATUS)
    _require(errors, 'PUBLIC_STATUS.md', public_status, f'Current source version: `{version}`.')
    _require(errors, 'PUBLIC_STATUS.md', public_status, f'Source release label: `{EXPECTED_RELEASE_LABEL}`.')
    _require(errors, 'PUBLIC_STATUS.md', public_status, f'Publication status: **{EXPECTED_SOURCE_STATUS}**.')
    _require(errors, 'PUBLIC_STATUS.md', public_status, f'Latest published PyPI package: `{EXPECTED_DISTRIBUTION}=={LATEST_PUBLISHED_VERSION}` (`{LATEST_PUBLISHED_LABEL}`).')
    _require(errors, 'ROADMAP.md', roadmap, f'Current source package: `{EXPECTED_DISTRIBUTION}=={version}`')
    _require(errors, 'ROADMAP.md', roadmap, EXPECTED_SOURCE_STATUS)
    _require(errors, 'ROADMAP.md', roadmap, f'Latest published public package: `{EXPECTED_DISTRIBUTION}=={LATEST_PUBLISHED_VERSION}`')
    _require(errors, 'VALIDATION.md', validation, f'current `{EXPECTED_DISTRIBUTION}=={version}` source')
    _require(errors, 'VALIDATION.md', validation, EXPECTED_SOURCE_STATUS)
    _require(errors, 'SPEC.md', spec, f'Current source package is `{EXPECTED_DISTRIBUTION}=={version}`')
    _require(errors, 'SPEC.md', spec, EXPECTED_SOURCE_STATUS)
    _require(errors, 'docs/ARTIFACTS.md', artifact_docs, f'Current source package: `{EXPECTED_DISTRIBUTION}=={version}`')
    _require(errors, 'docs/ARTIFACTS.md', artifact_docs, EXPECTED_SOURCE_STATUS)
    _require(errors, 'PUBLICATION_CHECKLIST.md', publication, 'Source-versus-published truth')
    _require(errors, 'PUBLICATION_CHECKLIST.md', publication, 'current source version and source release label: `2.0.1`')
    _require(errors, 'PUBLICATION_CHECKLIST.md', publication, '`sclite-core==2.0.1`')
    _require(errors, 'VALIDATION.md', validation, 'python scripts/validate_public_truth.py')
    _require(errors, 'PUBLICATION_CHECKLIST.md', publication, 'python scripts/validate_public_truth.py')
    _require(errors, 'VALIDATION.md', validation, 'scripts/security_regression_gate.sh')
    _require(errors, 'PUBLICATION_CHECKLIST.md', publication, 'scripts/security_regression_gate.sh')
    _require(errors, '.github/workflows/ci.yml', workflow, 'scripts/security_regression_gate.sh')
    _require(errors, 'SPEC.md', spec, 'verification_result.v1')
    _require(errors, 'VALIDATION.md', validation, 'verification_result.v1')
    _require(errors, 'README.md', readme, 'verification_result')
    _require(errors, 'CHANGELOG.md', changelog, f'## {EXPECTED_RELEASE_LABEL} - 2026-07-30')
    _require(errors, 'CHANGELOG.md', changelog, f'Published the audited `{EXPECTED_DISTRIBUTION}=={LATEST_PUBLISHED_VERSION}` package line')
    _require(errors, 'docs/GOVENGINE_INTEGRATION_CONTRACT.md', integration_contract, 'contracts/consumer_imports.v1.json')
    _require(errors, 'docs/GOVENGINE_INTEGRATION_CONTRACT.md', integration_contract, 'coordinated GovEngine/RExecOp/Tecrax')
    _require(errors, 'docs/GOVENGINE_INTEGRATION_CONTRACT.md', integration_contract, 'domain profiles do not authorize execution')
    _require(errors, 'docs/INTEGRATION_GUIDE.md', integration_guide, 'contracts/consumer_imports.v1.json')
    _require(errors, 'docs/INTEGRATION_GUIDE.md', integration_guide, 'require_lifecycle=True')
    _require(errors, 'README.md', readme, 'Runtime dependencies are intentionally empty.')
    _require(errors, 'README.md', readme, f'Python import package remains `{EXPECTED_IMPORT_PACKAGE}`')
    _require(errors, 'CONTRIBUTING.md', _read('CONTRIBUTING.md'), 'define / validate / hash / bind / redact / review / verify')
    _require(errors, 'SPEC.md', spec, 'define / validate / hash / bind / redact / review / verify')
    _require(errors, 'SECURITY.md', _read('SECURITY.md'), f'current published stable package is `{EXPECTED_DISTRIBUTION}=={LATEST_PUBLISHED_VERSION}`')
    _require(errors, 'README.md', readme, 'SECURITY_MODEL.md')
    _require(errors, 'README.md', readme, 'docs/SECURITY_PROFILES.md')
    _require(errors, 'README.md', readme, 'docs/SCHEMA_COMPATIBILITY.md')
    _require(errors, 'SPEC.md', spec, 'Any incompatible change must use a new profile name')
    _require(errors, 'SPEC.md', spec, 'kernel_guard_hmac_v1')
    _require(errors, 'SPEC.md', spec, 'Supported schema-version combinations')
    _require(errors, 'VALIDATION.md', validation, 'transcript/canonicalization changes require a new profile name')
    _require(errors, 'PUBLICATION_CHECKLIST.md', publication, 'profile freeze docs remain aligned')
    _require(errors, 'SECURITY_MODEL.md', security_model, 'SCLite reports replay as `not_checked`')
    _require(errors, 'SECURITY_MODEL.md', security_model, '`validate-chain` returns `chain_status: passed`')
    _require(errors, 'SECURITY_MODEL.md', security_model, '`verify-guarded-chain` adds `guard_status: passed`')
    _require(errors, 'VALIDATION.md', validation, 'verify_lifecycle_manifest()')
    _require(errors, 'VALIDATION.md', validation, 'docs/SCHEMA_COMPATIBILITY.md')
    _require(errors, 'SPEC.md', spec, '`execution_shape.plan` remains an opaque normalized execution-shape field')
    _require(errors, 'SECURITY_MODEL.md', security_model, 'Any incompatible change requires a new profile name')
    _require(errors, 'SECURITY_MODEL.md', security_model, 'HMAC gives authenticity only to parties that already share the secret')
    _require(errors, 'SECURITY_MODEL.md', security_model, 'SCLite does not decide whether an action is authorized')
    _require(errors, 'SECURITY_MODEL.md', security_model, 'Production replay stores should provide atomic check-and-set behavior')
    _require(errors, 'SECURITY_MODEL.md', security_model, 'Artifact `schema_ref` values are treated as contract identifiers')
    _require(errors, 'SECURITY_MODEL.md', security_model, 'External schema files are available only through explicit caller opt-in')
    _require(errors, 'SECURITY_MODEL.md', security_model, 'Path-like aliases that merely end')
    _require(errors, 'SECURITY_MODEL.md', security_model, 'no fallback to repository-local schema files')
    _require(errors, 'SECURITY_MODEL.md', security_model, 'does not silently disable the guard sidecar shape check')
    _require(errors, 'SECURITY_MODEL.md', security_model, 'Host freshness handoff data')
    _require(errors, 'docs/GOVENGINE_INTEGRATION_CONTRACT.md', _read('docs/GOVENGINE_INTEGRATION_CONTRACT.md'), 'Replay persistence, TTL')
    _require(errors, 'VALIDATION.md', validation, 'Path validation rejects')
    schema_compat = _read('docs/SCHEMA_COMPATIBILITY.md')
    _require(errors, 'docs/SCHEMA_COMPATIBILITY.md', schema_compat, 'Unknown fields are metadata')
    _require(errors, 'docs/SCHEMA_COMPATIBILITY.md', schema_compat, 'Artifact IDs are labels unless')
    _require(errors, 'docs/SCHEMA_COMPATIBILITY.md', schema_compat, 'SCLite must not import GovEngine in production code')
    _require(errors, 'docs/SECURITY_PROFILES.md', security_profiles, '`guarded-strict`')
    _require(errors, 'docs/SECURITY_PROFILES.md', security_profiles, '`guarded_domain_auth_fresh`')
    _require(errors, 'docs/SECURITY_PROFILES.md', security_profiles, 'An incompatible change must use a new profile name')
    _require(errors, 'docs/SECURITY_PROFILES.md', security_profiles, 'replay freshness inside SCLite')
    _require(errors, 'docs/SECURITY_PROFILES.md', security_profiles, 'sidecar schema validation remains enforced independently')
    _require(errors, '.github/workflows/ci.yml', workflow, 'actions/checkout@df4cb1c069e1874edd31b4311f1884172cec0e10')
    _require(errors, '.github/workflows/ci.yml', workflow, 'actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1')
    _require(errors, '.github/workflows/ci.yml', workflow, "python-version: ['3.11', '3.12', '3.13']")
    _require(errors, '.github/workflows/ci.yml', workflow, 'scripts/public_validation_gate.sh')
    _require(errors, '.github/workflows/ci.yml', workflow, 'scripts/strict_schema_gate.sh')
    _require(errors, '.github/workflows/ci.yml', workflow, 'package-dry-run:')
    _require(errors, '.github/workflows/ci.yml', workflow, 'rm -rf dist build *.egg-info')
    _require(errors, 'PUBLICATION_CHECKLIST.md', publication, 'scripts/package_smoke.sh')
    _require(errors, 'PUBLICATION_CHECKLIST.md', publication, 'product SBOM is generated after the exact wheel exists')
    _require(errors, 'docs/RELEASE_SECURITY.md', _read('docs/RELEASE_SECURITY.md'), 'product SBOM')
    _require(errors, 'VALIDATION.md', validation, 'release-readiness evidence only')
    _require(errors, '.github/workflows/ci.yml', workflow, 'python -m pip check')
    _assert_canonical_release_artifact_boundaries(
        errors,
        workflow=workflow,
        release_workflow=release_workflow,
        package_smoke=package_smoke,
        manifest=manifest,
    )
    _assert_product_sbom_workflow(
        errors,
        path='.github/workflows/ci.yml',
        workflow=workflow,
        output='dist/sclite-core.cdx.json',
    )
    _assert_product_sbom_workflow(
        errors,
        path='.github/workflows/release.yml',
        workflow=release_workflow,
        output='release-evidence/sclite-core.cdx.json',
    )

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
    errors.extend(_documentation_command_errors(active_markdown))
    errors.extend(_documentation_fixture_command_errors(active_markdown))
    errors.extend(_documentation_invocation_errors(active_markdown))
    errors.extend(_documentation_reference_errors(all_markdown))
    errors.extend(_current_document_wording_errors({
        path: _read(path) for path in active_markdown
    }))
    errors.extend(_forbidden_claim_errors(active_markdown))

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
