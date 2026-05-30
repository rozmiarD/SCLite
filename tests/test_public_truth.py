from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


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

    assert result.stdout.strip() == 'public_truth_ok:sclite-core==1.0.0rc1:import=sclite:runtime_deps=0'


def test_public_truth_validator_rejects_dynamic_prerelease_badge() -> None:
    validator = _load_validator()
    errors: list[str] = []

    validator._assert_readme_package_truth(errors, 'img.shields.io/pypi/v/sclite-core', '1.0.0rc1')

    assert 'README.md:prerelease_unsafe_package_claim:img.shields.io/pypi/v/sclite-core' in errors


def test_public_truth_validator_accepts_published_rc_install_claim() -> None:
    validator = _load_validator()
    errors: list[str] = []

    validator._assert_readme_package_truth(
        errors,
        '\n'.join([
            'Version: `1.0.0rc1`',
            'package-sclite--core%201.0.0rc1-blueviolet.svg',
            'https://pypi.org/project/sclite-core/1.0.0rc1/',
            'python -m pip install sclite-core==1.0.0rc1',
        ]),
        '1.0.0rc1',
    )

    assert errors == []


def test_public_truth_validator_rejects_stale_spec_current_package() -> None:
    validator = _load_validator()
    errors: list[str] = []

    validator._assert_current_claim_docs(
        errors,
        version='1.0.0rc1',
        readme=(
            'v1.0 release candidate\n'
            'Published current release candidate\n'
        ),
        roadmap=(
            '## 0.5.1 — GovEngine integration readiness\n\n'
            'Status: published predecessor patch line.\n'
        ),
        spec=(
            'Current package release is `sclite-core==0.5.1`\n'
            'Current package is `sclite-core==1.0.0rc1`\n'
            'The current front door is the review lifecycle substrate\n'
            'The superseded proof-trace product path is retired after Ravenclaw migrated to the\n'
            'current lifecycle/review-bundle front door.\n'
        ),
        artifact_docs=(
            'Current package: `sclite-core==1.0.0rc1`\n'
            'latest published public package: `sclite-core==1.0.0rc1`\n'
            'The current integration front door is the review lifecycle substrate\n'
            'The superseded proof-trace product path is retired after Ravenclaw\n'
        ),
        integration_guide='The current 1.0 release candidate freezes the review-bundle contract.\n',
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
            'Status: current alpha candidate implemented after Ravenclaw consumer migration.\n'
            'gates pass against the 0.8 candidate.\n'
        ),
    )

    assert (
        'ROADMAP.md:stale_published_candidate_claim:'
        'Status: current alpha candidate implemented after Ravenclaw consumer migration.'
    ) in errors


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
