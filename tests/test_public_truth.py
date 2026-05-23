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

    assert result.stdout.strip() == 'public_truth_ok:sclite-core==0.7.0a0:import=sclite:runtime_deps=0'


def test_public_truth_validator_rejects_dynamic_prerelease_badge() -> None:
    validator = _load_validator()
    errors: list[str] = []

    validator._assert_readme_package_truth(errors, 'img.shields.io/pypi/v/sclite-core', '0.7.0a0')

    assert 'README.md:prerelease_unsafe_package_claim:img.shields.io/pypi/v/sclite-core' in errors


def test_public_truth_validator_rejects_stale_spec_current_package() -> None:
    validator = _load_validator()
    errors: list[str] = []

    validator._assert_current_claim_docs(
        errors,
        version='0.7.0a0',
        readme=(
            'v0.7 alpha surface collapse\n'
            'Current alpha integration front door\n'
        ),
        roadmap=(
            '## 0.5.1 — GovEngine integration readiness\n\n'
            'Status: published predecessor patch line.\n'
        ),
        spec=(
            'Current package release is `sclite-core==0.5.1`\n'
            'The current front door is the review lifecycle substrate\n'
            'Legacy v0.1 proof-trace artifacts remain compatibility/history material; Ravenclaw\'s\n'
            'active path now consumes the current lifecycle/review-bundle front door.\n'
        ),
        artifact_docs=(
            'Current public package line: `sclite-core==0.7.0a0`\n'
            'The current integration front door is the review lifecycle substrate\n'
            'Legacy v0.1 artifacts are compatibility/history material for Ravenclaw\n'
        ),
        integration_guide='The current 0.7 alpha line curates the review-bundle contract.\n',
    )

    assert (
        'SPEC.md:stale_current_package_claim:'
        'Current package release is `sclite-core==0.5.1`'
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
