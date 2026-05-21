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

    assert result.stdout.strip() == 'public_truth_ok:sclite-core==0.6.0a0:import=sclite:runtime_deps=0'


def test_public_truth_validator_rejects_dynamic_prerelease_badge() -> None:
    validator = _load_validator()
    errors: list[str] = []

    validator._assert_readme_package_truth(errors, 'img.shields.io/pypi/v/sclite-core', '0.6.0a0')

    assert 'README.md:prerelease_unsafe_package_claim:img.shields.io/pypi/v/sclite-core' in errors
