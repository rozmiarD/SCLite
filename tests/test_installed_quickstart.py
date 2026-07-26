from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)


def test_packaged_lifecycle_quickstart_runs_from_an_empty_directory(tmp_path: Path) -> None:
    wheelhouse = tmp_path / 'wheelhouse'
    wheelhouse.mkdir()
    build = subprocess.run(
        [sys.executable, '-m', 'build', '--wheel', '--outdir', str(wheelhouse)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert build.returncode == 0, build.stderr
    wheel = next(wheelhouse.glob('*.whl'))

    environment = tmp_path / 'environment'
    create_venv = subprocess.run(
        [sys.executable, '-m', 'venv', str(environment)], text=True, capture_output=True, check=False
    )
    assert create_venv.returncode == 0, create_venv.stderr
    python = environment / 'bin' / 'python'
    install = subprocess.run(
        [str(python), '-m', 'pip', 'install', '--no-index', '--no-deps', str(wheel)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert install.returncode == 0, install.stderr

    empty_directory = tmp_path / 'empty'
    empty_directory.mkdir()
    installed_env = {key: value for key, value in os.environ.items() if key not in {'PYTHONHOME', 'PYTHONPATH'}}
    installed_env['PYTHONNOUSERSITE'] = '1'
    cli = environment / 'bin' / 'sclite'
    for command, expected in (
        (['validate-chain', '--example', 'contract-lifecycle-v0.2'], 'artifact_chain_ok:'),
        (['verify-lifecycle', '--example', 'contract-lifecycle-v0.2'], 'lifecycle_ok:'),
    ):
        result = _run([str(cli), *command], cwd=empty_directory, env=installed_env)
        assert result.returncode == 0, result.stderr
        assert expected in result.stdout
