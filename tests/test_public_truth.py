from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'validate_public_truth.py'


def _load_validator():
    spec = importlib.util.spec_from_file_location('sclite_validate_public_truth', SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_public_truth_validator_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert result.stdout.strip() == 'public_truth_ok:sclite-core==2.0.1:import=sclite:runtime_deps=0'


def test_public_truth_validator_rejects_tool_environment_sbom_before_wheel() -> None:
    validator = _load_validator()
    errors: list[str] = []
    workflow = '\n'.join((
        'name: Dependency audit and SBOM',
        'cyclonedx-py environment --output-file dist/sclite-core.cdx.json',
        'python -m build',
    ))

    validator._assert_product_sbom_workflow(
        errors,
        path='.github/workflows/ci.yml',
        workflow=workflow,
        output='dist/sclite-core.cdx.json',
    )

    assert '.github/workflows/ci.yml:tool_environment_sbom_forbidden' in errors
    assert '.github/workflows/ci.yml:product_sbom_must_follow_wheel_build' in errors
    assert '.github/workflows/ci.yml:dependency_audit_and_product_sbom_must_be_distinct' in errors


@pytest.mark.parametrize(
    ('workflow', 'expected_error'),
    (
        (
            '\n'.join((
                'python -m build',
                '# - name: Product SBOM',
                '# cyclonedx-py environment "${TARGET_VENV}/bin/python" --pyproject pyproject.toml --mc-type library --output-reproducible --output-file dist/sclite-core.cdx.json',
            )),
            '.github/workflows/ci.yml:product_sbom_step_count:0',
        ),
        (
            '\n'.join((
                '- name: Product SBOM',
                'TARGET_VENV="$(mktemp -d "${RUNNER_TEMP}/sclite-product-sbom.XXXXXX")"',
                'python -m venv --without-pip "${TARGET_VENV}"',
                'python -m pip --python "${TARGET_VENV}/bin/python" install --no-index --no-deps dist/*.whl',
                'cyclonedx-py environment "${TARGET_VENV}/bin/python" --pyproject pyproject.toml --mc-type library --output-reproducible --output-file dist/sclite-core.cdx.json',
                'python -m build',
                'python scripts/validate_product_sbom.py --wheel dist/*.whl --sbom dist/sclite-core.cdx.json',
            )),
            '.github/workflows/ci.yml:product_sbom_must_follow_wheel_build',
        ),
    ),
)
def test_public_truth_validator_rejects_comment_only_and_reordered_product_sbom(
    workflow: str, expected_error: str
) -> None:
    validator = _load_validator()
    errors: list[str] = []

    validator._assert_product_sbom_workflow(
        errors,
        path='.github/workflows/ci.yml',
        workflow=workflow,
        output='dist/sclite-core.cdx.json',
    )

    assert expected_error in errors


def test_public_truth_validator_rejects_dynamic_prerelease_badge() -> None:
    validator = _load_validator()
    errors: list[str] = []

    validator._assert_readme_package_truth(errors, 'img.shields.io/pypi/v/sclite-core', '1.0.0')

    assert 'README.md:prerelease_unsafe_package_claim:img.shields.io/pypi/v/sclite-core' in errors


def test_public_truth_validator_accepts_source_and_published_install_split() -> None:
    validator = _load_validator()
    errors: list[str] = []

    validator._assert_readme_package_truth(
        errors,
        '\n'.join([
            'Version: `2.0.1`',
            '[![Current source: sclite-core 2.0.1]'
            '(https://img.shields.io/badge/current%20source-sclite--core%202.0.1-blueviolet.svg)',
            'Release status: **unpublished non-prerelease 2.0.1 release source; '
            'publication pending**',
            'package-sclite--core%202.0.0-blueviolet.svg',
            'https://pypi.org/project/sclite-core/2.0.0/',
            'python -m pip install sclite-core==2.0.0',
        ]),
        '2.0.1',
    )

    assert errors == []


def test_public_truth_validator_accepts_unpublished_candidate_truth() -> None:
    validator = _load_validator()
    errors: list[str] = []

    validator._assert_unpublished_candidate_truth(
        errors,
        {
            'README.md': (
                'unpublished non-prerelease 2.0.1 release source; publication pending\n'
                'Latest published PyPI package: `sclite-core==2.0.0`.\n'
            ),
            'PUBLICATION_CHECKLIST.md': (
                'The `2.0.1` source must not be described as published or installable '
                'from PyPI.\n'
            ),
        },
        '2.0.1',
    )

    assert errors == []


@pytest.mark.parametrize(
    ('path', 'claim', 'error_kind'),
    (
        (
            'README.md',
            'https://pypi.org/project/sclite-core/2.0.1/',
            'unpublished_candidate_distribution_claim',
        ),
        (
            'VALIDATION.md',
            'python -m pip install sclite-core==2.0.1',
            'unpublished_candidate_distribution_claim',
        ),
        (
            'PUBLIC_STATUS.md',
            'Latest published PyPI package: `sclite-core==2.0.1`.',
            'unpublished_candidate_claimed_published',
        ),
        (
            'ROADMAP.md',
            'The 2.0.1 release source is published.',
            'unpublished_candidate_claimed_published',
        ),
    ),
)
def test_public_truth_validator_rejects_unpublished_candidate_distribution_claims(
    path: str,
    claim: str,
    error_kind: str,
) -> None:
    validator = _load_validator()
    errors: list[str] = []

    validator._assert_unpublished_candidate_truth(errors, {path: claim}, '2.0.1')

    assert any(error.startswith(f'{path}:') and error_kind in error for error in errors)


def test_public_truth_validator_requires_readme_project_metadata(monkeypatch) -> None:
    validator = _load_validator()
    project = validator._pyproject()
    project['readme'] = 'docs/OTHER.md'
    monkeypatch.setattr(validator, '_pyproject', lambda: project)

    assert 'project_readme_mismatch:docs/OTHER.md!=README.md' in validator.collect_errors()


@pytest.mark.parametrize(
    ('path', 'injected'),
    (
        (
            'README.md',
            '[![PyPI stable: sclite-core 2.0.1]'
            '(https://img.shields.io/badge/package-sclite--core%202.0.1-blueviolet.svg)]'
            '(pyproject.toml)',
        ),
        ('README.md', 'https://pypi.org/project/sclite-core/2.0.1/'),
        ('VALIDATION.md', 'python -m pip install sclite-core==2.0.1'),
        (
            'PUBLIC_STATUS.md',
            'Latest published PyPI package: `sclite-core==2.0.1`.',
        ),
        ('ROADMAP.md', 'The 2.0.1 release source is published.'),
        (
            'PUBLIC_STATUS.md',
            'Published SCLite 2.0.1 to PyPI.',
        ),
        (
            'ROADMAP.md',
            'Previously unpublished, SCLite 2.0.1 is published on PyPI.',
        ),
        ('PUBLIC_STATUS.md', 'SCLite 2.0.1 is available from PyPI.'),
        (
            'VALIDATION.md',
            'Install from PyPI: python -m pip install --no-deps '
            'sclite-core==2.0.1',
        ),
        (
            'VALIDATION.md',
            "Install from PyPI: python -m pip install --no-deps "
            "'sclite-core==2.0.1'",
        ),
        ('CHANGELOG.md', 'Released sclite-core 2.0.1 on PyPI.'),
        ('PUBLIC_STATUS.md', 'sclite-core==2.0.1 is now on PyPI.'),
        ('PUBLIC_STATUS.md', 'PyPI now hosts sclite-core 2.0.1.'),
        ('README.md', 'Install sclite-core==2.0.1 from PyPI.'),
        (
            'PUBLIC_STATUS.md',
            'SCLite 2.0.1 is published to PyPI; publication pending.',
        ),
        (
            'PUBLIC_STATUS.md',
            'SCLite 2.0.1 is available from PyPI; publication pending.',
        ),
        (
            'PUBLIC_STATUS.md',
            'SCLite 2.0.1 is unpublished, but SCLite 2.0.1 is published on PyPI.',
        ),
    ),
)
def test_collect_errors_rejects_candidate_publication_matrix(
    monkeypatch,
    path: str,
    injected: str,
) -> None:
    validator = _load_validator()
    original_read = validator._read

    def read_with_candidate_claim(requested: str) -> str:
        text = original_read(requested)
        if requested == path:
            return f'{text}\n{injected}\n'
        return text

    monkeypatch.setattr(validator, '_read', read_with_candidate_claim)

    assert any(
        error.startswith(f'{path}:') and 'unpublished_candidate_' in error
        for error in validator.collect_errors()
    )


@pytest.mark.parametrize(
    'injected',
    (
        'Current source 2.0.1 and latest published PyPI package is '
        'sclite-core==2.0.0.',
        'Latest published PyPI package: sclite-core==2.0.0; '
        'current source: 2.0.1.',
        'SCLite 2.0.1 has not been published to PyPI; publication pending.',
        'The 2.0.1 source must not be described as published or installable '
        'from PyPI.',
        'The latest published audit documents source 2.0.1.',
    ),
)
def test_collect_errors_accepts_candidate_publication_matrix(
    monkeypatch,
    injected: str,
) -> None:
    validator = _load_validator()
    original_read = validator._read

    def read_with_candidate_truth(requested: str) -> str:
        text = original_read(requested)
        if requested == 'PUBLIC_STATUS.md':
            return f'{text}\n{injected}\n'
        return text

    monkeypatch.setattr(validator, '_read', read_with_candidate_truth)

    assert validator.collect_errors() == []


def test_public_truth_validator_rejects_stale_spec_current_package() -> None:
    validator = _load_validator()
    errors: list[str] = []

    validator._assert_current_claim_docs(
        errors,
        version='2.0.1',
        readme=(
            'unpublished non-prerelease 2.0.1 release source; publication pending\n'
            'Development Status :: 4 - Beta\n'
            '## Out of Scope\n'
            'Runtime execution: out of scope; owned by RExecOp or another host runtime\n'
            'GovEngine | governance, admission, policy decisions\n'
            'RExecOp | domain-neutral lifecycle runner\n'
            'When `--guard` is provided explicitly, SCLite resolves it relative to the\n'
        ),
        roadmap=(
            'SCLite 2.0 is the frozen truth\n'
            '## 2.0 maintenance policy\n'
            'feature-freeze-compatible maintenance source\n'
        ),
        spec=(
            'Current package release is `sclite-core==0.5.1`\n'
            'Current source package is `sclite-core==2.0.1`\n'
            'The current front door is the review lifecycle substrate\n'
            'The superseded proof-trace product path is retired after controlled consumers\n'
            'current lifecycle/review-bundle front door.\n'
        ),
        artifact_docs=(
            'Current source package: `sclite-core==2.0.1`\n'
            'latest published public package: `sclite-core==2.0.0`\n'
            'The current integration front door is the review lifecycle substrate\n'
            'The superseded proof-trace product path is retired after Ravenclaw\n'
        ),
        integration_guide='The current 2.0 stable release freezes the review-bundle contract.\n',
    )

    assert (
        'SPEC.md:stale_current_package_claim:'
        'Current package release is `sclite-core==0.5.1`'
    ) in errors


def test_public_truth_validator_rejects_candidate_wording_for_published_roadmap_line() -> None:
    validator = _load_validator()
    errors: list[str] = []

    validator._assert_roadmap_release_truth(
        errors,
        (
            'Status: current alpha line implemented for validation and downstream migration.\n'
            'Delivered in the current candidate:\n'
            'Status: published current stable release.\n'
        ),
    )

    assert (
        'ROADMAP.md:historical_line_in_active_roadmap:Status: current alpha'
    ) in errors


def test_documentation_cli_owner_is_derived_from_command_registry() -> None:
    validator = _load_validator()
    path = 'tests/fixture-cli-doc.md'
    validator._read = lambda requested: (
        'sclite review-lifecycle manifest.json\n'
        'python -m sclite.devtools validate-artifact --schema demo artifact.json\n'
        if requested == path
        else ''
    )

    assert validator._documentation_command_errors((path,)) == [
        f'{path}:1:documentation_cli_owner_mismatch:'
        'review-lifecycle:sclite!=sclite-devtools',
        f'{path}:2:documentation_cli_owner_mismatch:'
        'validate-artifact:sclite-devtools!=sclite',
    ]


def test_documentation_cli_registry_rejects_unknown_command_lines(
    monkeypatch,
) -> None:
    validator = _load_validator()
    path = 'tests/fixture-cli-typo-doc.md'
    monkeypatch.setattr(
        validator,
        '_read',
        lambda requested: (
            'sclite valdate-chain manifest.json\n'
            'from sclite import VerificationPolicy\n'
            if requested == path
            else ''
        ),
    )

    assert validator._documentation_command_errors((path,)) == [
        f'{path}:1:documentation_unknown_cli_command:valdate-chain',
    ]


def test_markdown_inventory_includes_nested_docs_and_excludes_generated_trees(
    tmp_path: Path,
    monkeypatch,
) -> None:
    golden = tmp_path / 'tests' / 'golden' / 'profile'
    golden.mkdir(parents=True)
    (golden / 'README.md').write_text('golden\n', encoding='utf-8')
    generated = tmp_path / 'build' / 'lib'
    generated.mkdir(parents=True)
    (generated / 'README.md').write_text('generated\n', encoding='utf-8')
    validator = _load_validator()
    monkeypatch.setattr(validator, 'ROOT', tmp_path)

    assert validator._markdown_paths(include_archive=True) == (
        'tests/golden/profile/README.md',
    )


def test_documentation_reference_check_rejects_missing_test(monkeypatch) -> None:
    validator = _load_validator()
    path = 'tests/fixture-reference-doc.md'
    monkeypatch.setattr(
        validator,
        '_read',
        lambda requested: 'Run tests/test_removed_surface.py\n' if requested == path else '',
    )

    assert validator._documentation_reference_errors((path,)) == [
        f'{path}:documentation_missing_test_reference:tests/test_removed_surface.py'
    ]


def test_documentation_fixture_command_rejects_schema_drift(
    tmp_path: Path,
    monkeypatch,
) -> None:
    validator = _load_validator()
    artifact = tmp_path / 'artifact.json'
    artifact.write_text(
        '{"artifact_type":"redaction_policy","schema_version":"v0.2"}',
        encoding='utf-8',
    )
    path = 'tests/fixture-schema-doc.md'
    monkeypatch.setattr(validator, 'ROOT', tmp_path)
    monkeypatch.setattr(
        validator,
        '_read',
        lambda requested: (
            'sclite validate-artifact --schema redaction_policy.v0.1 artifact.json\n'
            if requested == path
            else ''
        ),
    )

    assert validator._documentation_fixture_command_errors((path,)) == [
        f'{path}:documentation_example_schema_mismatch:'
        'artifact.json:redaction_policy.v0.1!=redaction_policy.v0.2'
    ]


def test_documentation_invocation_rejects_unsupported_consumer_validator_flags(
    monkeypatch,
) -> None:
    validator = _load_validator()
    path = 'tests/fixture-consumer-validator-doc.md'
    monkeypatch.setattr(
        validator,
        '_read',
        lambda requested: (
            'python scripts/validate_forbidden_consumer_imports.py '
            '--govengine ../govengine --rexecop ../rexecop --tecrax ../tecrax\n'
            if requested == path
            else ''
        ),
    )

    assert validator._documentation_invocation_errors((path,)) == [
        f'{path}:1:documentation_consumer_validator_unsupported_flag:--govengine',
        f'{path}:1:documentation_consumer_validator_unsupported_flag:--rexecop',
        f'{path}:1:documentation_consumer_validator_unsupported_flag:--tecrax',
    ]


def test_documentation_invocation_requires_local_review_for_governance_fixture(
    monkeypatch,
) -> None:
    validator = _load_validator()
    path = 'tests/fixture-review-export-doc.md'
    monkeypatch.setattr(
        validator,
        '_read',
        lambda requested: (
            'sclite export-review-bundle examples/govengine-integration '
            '--format markdown\n'
            if requested == path
            else ''
        ),
    )

    assert validator._documentation_invocation_errors((path,)) == [
        f'{path}:1:documentation_govengine_export_requires_local_review'
    ]


def test_documentation_invocation_accepts_equals_form_for_local_review(
    monkeypatch,
) -> None:
    validator = _load_validator()
    path = 'tests/fixture-review-export-doc.md'
    monkeypatch.setattr(
        validator,
        '_read',
        lambda requested: (
            'sclite export-review-bundle examples/govengine-integration '
            '--mode=local_review --format markdown\n'
            if requested == path
            else ''
        ),
    )

    assert validator._documentation_invocation_errors((path,)) == []


def test_current_wording_and_forbidden_claims_scan_all_active_markdown(
    monkeypatch,
) -> None:
    validator = _load_validator()
    path = 'docs/THREAT_MODEL.md'
    monkeypatch.setattr(validator, '_markdown_paths', lambda *, include_archive: (path,))
    monkeypatch.setattr(
        validator,
        '_read',
        lambda requested: (
            'Frozen for the 1.0 line. SCLite is production-ready.\n'
            if requested == path
            else ''
        ),
    )

    active = validator._markdown_paths(include_archive=False)
    assert validator._current_document_wording_errors({
        item: validator._read(item) for item in active
    }) == [
        f'{path}:stale_current_release_wording:for the 1.0 line',
    ]
    assert validator._forbidden_claim_errors(active) == [
        f'{path}:1:forbidden_overclaim:production-ready',
    ]


def test_current_docs_reject_stale_release_and_removed_schema_claims() -> None:
    validator = _load_validator()

    assert validator._current_document_wording_errors({
        'VALIDATION.md': (
            'Frozen for the 1.0 line. Current artifact automation_chain.v0.1.\n'
        ),
    }) == [
        'VALIDATION.md:stale_current_release_wording:for the 1.0 line',
        'VALIDATION.md:removed_schema_advertised_in_current_docs:automation_chain.v0.1',
    ]


def test_public_truth_validator_rejects_legacy_root_exports() -> None:
    validator = _load_validator()
    original = validator.sclite.__all__
    try:
        validator.sclite.__all__ = (*original, 'build_proof_trace_artifacts')
        assert (
            'root_api_exports_legacy_surface:build_proof_trace_artifacts'
            in validator._curated_root_export_errors()
        )
    finally:
        validator.sclite.__all__ = original


def test_current_public_surface_index_excludes_legacy_proof_trace_front_door() -> None:
    validator = _load_validator()

    assert validator._surface_fixture_errors() == []
    surface_paths = {
        surface['path']
        for surface in validator.build_public_validation_surface_index(
            generated_at='2026-05-24T00:00:00+00:00'
        )['surfaces']
    }
    assert not surface_paths.intersection(validator.RETIRED_CURRENT_SURFACE_PATHS)


def test_current_public_snapshot_manifest_excludes_legacy_proof_trace() -> None:
    validator = _load_validator()

    assert validator._snapshot_fixture_errors() == []


def test_retired_proof_trace_product_paths_stay_absent() -> None:
    validator = _load_validator()

    assert validator._retired_product_errors() == []


def test_retained_fixture_rejects_reference_to_retired_product_path() -> None:
    validator = _load_validator()

    assert validator._retired_reference_errors({
        'examples/scope-fidelity-report/scope_fidelity_report.json':
            '{"source_artifact": "examples/security-contract-proof/approved_execution_spec.json"}',
    }) == [
        'examples/scope-fidelity-report/scope_fidelity_report.json:references_retired_product_path',
    ]


def test_current_fixture_docs_reject_retired_or_maturity_ambiguous_wording() -> None:
    validator = _load_validator()

    assert validator._documentation_drift_errors({
        'examples/bad-review-bundle-cross-host/README.md':
            'the prepared execution/ticket target remains unchanged',
        'examples/trust-carrier-profiles/README.md':
            'bound to the published v0.3 scoped-ticket artifact',
    }) == [
        'examples/bad-review-bundle-cross-host/README.md:stale_current_wording:'
        'prepared execution/ticket target',
        'examples/trust-carrier-profiles/README.md:stale_current_wording:'
        'published v0.3 scoped-ticket artifact',
    ]
