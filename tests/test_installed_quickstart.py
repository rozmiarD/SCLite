from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False, timeout=30)


def test_packaged_lifecycle_quickstart_runs_from_an_empty_directory(tmp_path: Path) -> None:
    wheelhouse = tmp_path / 'wheelhouse'
    wheelhouse.mkdir()
    build = subprocess.run(
        [sys.executable, '-m', 'pip', 'wheel', '--no-deps', '--wheel-dir', str(wheelhouse), '.'],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    assert build.returncode == 0, build.stderr
    wheel = next(wheelhouse.glob('*.whl'))

    environment = tmp_path / 'environment'
    create_venv = subprocess.run(
        [sys.executable, '-m', 'venv', str(environment)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    assert create_venv.returncode == 0, create_venv.stderr
    python = environment / 'bin' / 'python'

    empty_directory = tmp_path / 'empty'
    empty_directory.mkdir()
    installed_env = {key: value for key, value in os.environ.items() if key not in {'PYTHONHOME', 'PYTHONPATH'}}
    installed_env['PYTHONNOUSERSITE'] = '1'
    install = subprocess.run(
        [str(python), '-m', 'pip', 'install', '--no-index', '--no-deps', str(wheel)],
        cwd=empty_directory,
        env=installed_env,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    assert install.returncode == 0, install.stderr

    cli = environment / 'bin' / 'sclite'
    resource = _run(
        [
            str(python),
            '-c',
            'from importlib.resources import files; '
            'print(files("sclite.examples").joinpath('
            '"contract-lifecycle-v0.2", "artifact_chain_manifest.json"))',
        ],
        cwd=empty_directory,
        env=installed_env,
    )
    assert resource.returncode == 0, resource.stderr
    manifest = Path(resource.stdout.strip())
    assert manifest.is_file()

    for command, expected in (
        ('validate-chain', 'artifact_chain_ok:'),
        ('verify-lifecycle', 'lifecycle_ok:'),
    ):
        result = _run([str(cli), command, str(manifest)], cwd=empty_directory, env=installed_env)
        assert result.returncode == 0, result.stderr
        assert expected in result.stdout
