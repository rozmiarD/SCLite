from __future__ import annotations

import importlib.util
import io
import tarfile
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'validate_distribution_metadata.py'
ROOT_NAME = 'sclite_core-2.0.1'


def _load_validator():
    spec = importlib.util.spec_from_file_location('sclite_validate_distribution_metadata', SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _metadata(
    *,
    name: str = 'sclite-core',
    version: str = '2.0.1',
    content_type: str = 'text/markdown',
    description: bytes | None = None,
) -> bytes:
    if description is None:
        description = (ROOT / 'PYPI_LONG_DESCRIPTION.md').read_bytes()
    headers = (
        f'Name: {name}\nVersion: {version}\n'
        f'Description-Content-Type: {content_type}\n\n'
    ).encode('utf-8')
    return headers + description


def _regular(archive: tarfile.TarFile, name: str, content: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(content)
    archive.addfile(info, io.BytesIO(content))


def _artifacts(
    tmp_path: Path,
    *,
    wheel_metadata: bytes | None = None,
    sdist_metadata: bytes | None = None,
) -> tuple[Path, Path]:
    metadata = _metadata()
    wheel = tmp_path / 'sclite_core-2.0.1-py3-none-any.whl'
    with zipfile.ZipFile(wheel, 'w') as archive:
        archive.writestr(f'{ROOT_NAME}.dist-info/METADATA', wheel_metadata or metadata)

    sdist = tmp_path / 'sclite_core-2.0.1.tar.gz'
    with tarfile.open(sdist, 'w:gz') as archive:
        _regular(archive, f'{ROOT_NAME}/PKG-INFO', sdist_metadata or metadata)
        _regular(archive, f'{ROOT_NAME}/sclite_core.egg-info/PKG-INFO', metadata)
        _regular(archive, f'{ROOT_NAME}/scripts/validate_distribution_metadata.py', b'pass\n')
        _regular(archive, f'{ROOT_NAME}/scripts/build_release_artifacts.sh', b'exit 0\n')
    return wheel, sdist


def test_accepts_setuptools_shaped_sdist_with_nested_egg_info(tmp_path: Path) -> None:
    validator = _load_validator()
    wheel, sdist = _artifacts(tmp_path)

    validator.validate_distribution_metadata(wheel=wheel, sdist=sdist)


@pytest.mark.parametrize(
    ('wheel_metadata', 'sdist_metadata', 'expected'),
    (
        (_metadata(name='other'), None, 'wheel:name:other!=sclite-core'),
        (_metadata(version='2.0.0'), None, 'wheel:version:2.0.0!=2.0.1'),
        (_metadata(content_type='text/plain'), None, 'wheel:description_content_type:text/plain'),
        (_metadata(description=b'different\n'), None, 'wheel:description_mismatch:source'),
        (None, _metadata(name='other'), 'sdist:name:other!=sclite-core'),
        (None, _metadata(version='2.0.0'), 'sdist:version:2.0.0!=2.0.1'),
        (None, _metadata(content_type='text/plain'), 'sdist:description_content_type:text/plain'),
        (None, _metadata(description=b'different\n'), 'sdist:description_mismatch:source'),
    ),
)
def test_rejects_identity_or_payload_mismatch(
    tmp_path: Path, wheel_metadata: bytes | None, sdist_metadata: bytes | None, expected: str
) -> None:
    validator = _load_validator()
    wheel, sdist = _artifacts(
        tmp_path, wheel_metadata=wheel_metadata, sdist_metadata=sdist_metadata
    )

    with pytest.raises(validator.MetadataValidationError, match=expected):
        validator.validate_distribution_metadata(wheel=wheel, sdist=sdist)


def test_rejects_missing_exact_wheel_metadata(tmp_path: Path) -> None:
    validator = _load_validator()
    wheel, sdist = _artifacts(tmp_path)
    replacement = tmp_path / 'missing.whl'
    with zipfile.ZipFile(replacement, 'w') as archive:
        archive.writestr('other.dist-info/METADATA', _metadata())

    with pytest.raises(validator.MetadataValidationError, match='wheel_metadata:exact_member_count:0'):
        validator.validate_distribution_metadata(wheel=replacement, sdist=sdist)


def test_rejects_duplicate_exact_wheel_metadata(tmp_path: Path) -> None:
    validator = _load_validator()
    wheel, sdist = _artifacts(tmp_path)
    with zipfile.ZipFile(wheel, 'a') as archive:
        archive.writestr(f'{ROOT_NAME}.dist-info/METADATA', _metadata())

    with pytest.raises(validator.MetadataValidationError, match='wheel_metadata:exact_member_count:2'):
        validator.validate_distribution_metadata(wheel=wheel, sdist=sdist)


def test_rejects_nonregular_exact_wheel_metadata(tmp_path: Path) -> None:
    validator = _load_validator()
    _, sdist = _artifacts(tmp_path)
    wheel = tmp_path / 'link.whl'
    with zipfile.ZipFile(wheel, 'w') as archive:
        info = zipfile.ZipInfo(f'{ROOT_NAME}.dist-info/METADATA')
        info.create_system = 3
        info.external_attr = 0o120777 << 16
        archive.writestr(info, 'target')

    with pytest.raises(validator.MetadataValidationError, match='wheel_metadata:not_regular'):
        validator.validate_distribution_metadata(wheel=wheel, sdist=sdist)


@pytest.mark.parametrize('kind', ('missing', 'duplicate', 'link'))
def test_rejects_invalid_exact_root_sdist_metadata(tmp_path: Path, kind: str) -> None:
    validator = _load_validator()
    wheel, _ = _artifacts(tmp_path)
    sdist = tmp_path / f'{kind}.tar.gz'
    with tarfile.open(sdist, 'w:gz') as archive:
        if kind != 'missing':
            if kind == 'link':
                info = tarfile.TarInfo(f'{ROOT_NAME}/PKG-INFO')
                info.type = tarfile.SYMTYPE
                info.linkname = 'other'
                archive.addfile(info)
            else:
                _regular(archive, f'{ROOT_NAME}/PKG-INFO', _metadata())
                _regular(archive, f'{ROOT_NAME}/PKG-INFO', _metadata())
        _regular(archive, f'{ROOT_NAME}/sclite_core.egg-info/PKG-INFO', _metadata())
        _regular(archive, f'{ROOT_NAME}/scripts/validate_distribution_metadata.py', b'pass\n')
        _regular(archive, f'{ROOT_NAME}/scripts/build_release_artifacts.sh', b'exit 0\n')

    expected = 'sdist_root_pkg_info:not_regular' if kind == 'link' else (
        f'sdist_root_pkg_info:exact_member_count:{0 if kind == "missing" else 2}'
    )
    with pytest.raises(validator.MetadataValidationError, match=expected):
        validator.validate_distribution_metadata(wheel=wheel, sdist=sdist)


def test_rejects_duplicate_required_metadata_header(tmp_path: Path) -> None:
    validator = _load_validator()
    malformed = b'Name: sclite-core\nName: sclite-core\nVersion: 2.0.1\nDescription-Content-Type: text/markdown\n\nbody\n'
    wheel, sdist = _artifacts(tmp_path, wheel_metadata=malformed)

    with pytest.raises(validator.MetadataValidationError, match='wheel:Name:count:2'):
        validator.validate_distribution_metadata(wheel=wheel, sdist=sdist)


def test_rejects_crlf_source_against_lf_metadata(tmp_path: Path, monkeypatch) -> None:
    validator = _load_validator()
    wheel, sdist = _artifacts(tmp_path)
    source_root = tmp_path / 'source'
    source_root.mkdir()
    (source_root / 'pyproject.toml').write_text(
        '[project]\nname = "sclite-core"\nversion = "2.0.1"\nreadme = "PYPI_LONG_DESCRIPTION.md"\n',
        encoding='utf-8',
    )
    source_root.joinpath('PYPI_LONG_DESCRIPTION.md').write_bytes(
        (ROOT / 'PYPI_LONG_DESCRIPTION.md').read_bytes().replace(b'\n', b'\r\n')
    )
    monkeypatch.setattr(validator, 'ROOT', source_root)

    with pytest.raises(validator.MetadataValidationError, match='wheel:description_mismatch:source'):
        validator.validate_distribution_metadata(wheel=wheel, sdist=sdist)
