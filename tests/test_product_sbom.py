from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'validate_product_sbom.py'


def _load_validator():
    spec = importlib.util.spec_from_file_location('sclite_validate_product_sbom', SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_wheel(tmp_path: Path, metadata: str | None = None) -> Path:
    wheel = tmp_path / 'sclite_core-2.0.1-py3-none-any.whl'
    with zipfile.ZipFile(wheel, 'w') as archive:
        archive.writestr(
            'sclite_core-2.0.1.dist-info/METADATA',
            metadata or 'Name: sclite-core\nVersion: 2.0.1\n',
        )
    return wheel


def _product_sbom() -> dict[str, object]:
    return {
        'metadata': {
            'component': {
                'bom-ref': 'pkg:pypi/sclite-core@2.0.1',
                'type': 'library',
                'name': 'sclite-core',
                'version': '2.0.1',
            },
            'properties': [{'name': 'cdx:reproducible', 'value': 'true'}],
            'tools': {'components': [{'type': 'application', 'name': 'cyclonedx-py'}]},
        },
        'components': [],
        'dependencies': [{'ref': 'pkg:pypi/sclite-core@2.0.1', 'dependsOn': []}],
    }


def _write_sbom(tmp_path: Path, document: dict[str, object]) -> Path:
    sbom = tmp_path / 'sclite-core.cdx.json'
    sbom.write_text(json.dumps(document), encoding='utf-8')
    return sbom


def test_product_sbom_validator_binds_wheel_and_prints_sha256(tmp_path: Path) -> None:
    wheel = _write_wheel(tmp_path)
    sbom = _write_sbom(tmp_path, _product_sbom())

    result = subprocess.run(
        [sys.executable, str(SCRIPT), '--wheel', str(wheel), '--sbom', str(sbom)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert result.stdout.startswith('product_sbom_ok:sclite-core==2.0.1:wheel_sha256=')


@pytest.mark.parametrize(
    ('mutate', 'expected_error'),
    (
        (
            lambda document: document['metadata']['component'].__setitem__('name', 'other'),
            'component_name_mismatch:other!=sclite-core',
        ),
        (
            lambda document: document['metadata']['component'].__setitem__('version', '9.9.9'),
            'component_version_mismatch:9.9.9!=2.0.1',
        ),
        (
            lambda document: document['metadata']['component'].__setitem__('type', 'application'),
            'component_type_mismatch:application!=library',
        ),
        (
            lambda document: document['metadata'].__setitem__('properties', []),
            'metadata_reproducible_missing_or_false',
        ),
        (
            lambda document: document.__setitem__(
                'components', [{'type': 'application', 'name': 'cyclonedx-py'}]
            ),
            'generator_tool_leaked_into_components:cyclonedx-py',
        ),
    ),
)
def test_product_sbom_validator_rejects_product_identity_and_tool_leaks(
    tmp_path: Path, mutate, expected_error: str
) -> None:
    validator = _load_validator()
    wheel = _write_wheel(tmp_path)
    document = _product_sbom()
    mutate(document)
    sbom = _write_sbom(tmp_path, document)

    assert expected_error in validator.collect_errors(wheel=wheel, sbom=sbom)


def test_product_sbom_validator_rejects_unconditional_runtime_dependency(tmp_path: Path) -> None:
    validator = _load_validator()
    wheel = _write_wheel(tmp_path)
    document = _product_sbom()
    document['dependencies'] = [{
        'ref': 'pkg:pypi/sclite-core@2.0.1',
        'dependsOn': ['pkg:pypi/runtime-dependency@1.0.0'],
    }]
    sbom = _write_sbom(tmp_path, document)

    assert 'root_unconditional_runtime_dependencies_not_empty' in validator.collect_errors(
        wheel=wheel, sbom=sbom
    )


@pytest.mark.parametrize(
    ('metadata', 'expected_error'),
    (
        (
            'Name: sclite-core\nVersion: 2.0.1\nRequires-Dist: runtime-dependency>=1\n',
            'wheel_metadata_requires_dist_not_extra_guarded:runtime-dependency>=1',
        ),
        (
            'Name: sclite-core\nName: forged\nVersion: 2.0.1\n',
            'wheel_metadata_name_count:2',
        ),
        (
            'Name: sclite-core\nVersion: 2.0.1\nRequires-Dist: runtime; python_version >= "3.11"\n',
            'wheel_metadata_requires_dist_not_extra_guarded:runtime; python_version >= "3.11"',
        ),
        (
            'Name: sclite-core\nVersion: 2.0.1\nRequires-Dist: not a requirement\n',
            'wheel_metadata_requires_dist_invalid:not a requirement',
        ),
        (
            'Name: sclite-core\nVersion: 2.0.1\nProvides-Extra: optional\nProvides-Extra: optional\n',
            'wheel_metadata_provides_extra_not_unique',
        ),
        (
            'Name: sclite-core\nVersion: 2.0.1\nProvides-Extra: optional\nRequires-Dist: runtime; extra == "other"\n',
            'wheel_metadata_requires_dist_extra_undeclared:runtime; extra == "other"',
        ),
    ),
)
def test_product_sbom_validator_rejects_forged_wheel_metadata(
    tmp_path: Path, metadata: str, expected_error: str
) -> None:
    validator = _load_validator()
    wheel = _write_wheel(tmp_path, metadata)
    sbom = _write_sbom(tmp_path, _product_sbom())

    assert f'wheel_metadata_invalid:{expected_error}' in validator.collect_errors(
        wheel=wheel, sbom=sbom
    )


@pytest.mark.parametrize(
    ('document', 'expected_key'),
    (
        (
            '{"metadata":{},"metadata":{}}',
            'metadata',
        ),
        (
            '{"metadata":{"component":{"bom-ref":"pkg:pypi/sclite-core@2.0.1",'
            '"type":"library","name":"sclite-core","name":"forged","version":"2.0.1"}}}',
            'name',
        ),
    ),
)
def test_product_sbom_validator_rejects_duplicate_json_keys_at_any_nesting(
    tmp_path: Path, document: str, expected_key: str
) -> None:
    validator = _load_validator()
    wheel = _write_wheel(tmp_path)
    sbom = tmp_path / 'sclite-core.cdx.json'
    sbom.write_text(document, encoding='utf-8')

    assert validator.collect_errors(wheel=wheel, sbom=sbom) == [
        f'sbom_invalid_json:duplicate_json_key:{expected_key}'
    ]


def test_product_sbom_validator_rejects_orphan_dependency_entries(tmp_path: Path) -> None:
    validator = _load_validator()
    wheel = _write_wheel(tmp_path)
    document = _product_sbom()
    document['dependencies'] = [
        {'ref': 'pkg:pypi/sclite-core@2.0.1', 'dependsOn': []},
        {'ref': 'pkg:pypi/orphan@1.0.0', 'dependsOn': []},
    ]
    sbom = _write_sbom(tmp_path, document)

    assert 'dependency_entry_count:2' in validator.collect_errors(wheel=wheel, sbom=sbom)
