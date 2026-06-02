from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from sclite.artifacts import SCHEMA_FILES, JsonSchemaValidationError, load_json_schema, schema_dir, validate_artifact

ROOT = Path(__file__).resolve().parents[1]


def test_schema_registry_covers_all_packaged_schema_files() -> None:
    packaged = {path.name for path in schema_dir().glob('*.schema.json')}
    registered = set(SCHEMA_FILES.values())

    assert packaged == registered


def test_artifact_schema_ref_uses_packaged_schema_before_bundle_local_schema(tmp_path: Path) -> None:
    local_schema_dir = tmp_path / 'schemas'
    local_schema_dir.mkdir()
    (local_schema_dir / 'intent_contract.v0.2.schema.json').write_text(
        json.dumps({'type': 'object', 'additionalProperties': True}) + '\n',
        encoding='utf-8',
    )
    artifact = {
        'artifact_type': 'intent_contract',
        'schema_version': 'v0.2',
        'schema_ref': 'schemas/intent_contract.v0.2.schema.json',
    }

    with pytest.raises(JsonSchemaValidationError, match='missing required field'):
        validate_artifact(artifact, artifact['schema_ref'], root=tmp_path)


def test_packaged_schema_resolution_rejects_path_injection_aliases() -> None:
    with pytest.raises(JsonSchemaValidationError, match='not a packaged SCLite schema'):
        validate_artifact({}, '/tmp/intent_contract.v0.2.schema.json')
    with pytest.raises(JsonSchemaValidationError, match='not a packaged SCLite schema'):
        validate_artifact({}, 'schemas/../intent_contract.v0.2.schema.json')


def test_external_schema_ref_requires_explicit_opt_in(tmp_path: Path) -> None:
    schema_path = tmp_path / 'custom.schema.json'
    schema_path.write_text(
        json.dumps(
            {
                'type': 'object',
                'required': ['custom'],
                'properties': {'custom': {'const': True}},
                'additionalProperties': False,
            }
        )
        + '\n',
        encoding='utf-8',
    )
    value = {'custom': True}

    with pytest.raises(JsonSchemaValidationError, match='external schema refs require'):
        validate_artifact(value, str(schema_path), root=tmp_path)

    validate_artifact(value, str(schema_path), root=tmp_path, allow_external_schema_refs=True)


def test_external_schema_ref_opt_in_rejects_root_relative_escape(tmp_path: Path) -> None:
    root = tmp_path / 'bundle'
    root.mkdir()
    outside_schema = tmp_path / 'outside.schema.json'
    outside_schema.write_text(
        json.dumps({'type': 'object', 'additionalProperties': True}) + '\n',
        encoding='utf-8',
    )

    with pytest.raises(JsonSchemaValidationError, match='external schema path escapes root'):
        validate_artifact({}, '../outside.schema.json', root=root, allow_external_schema_refs=True)


def test_external_schema_ref_opt_in_rejects_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / 'bundle'
    root.mkdir()
    outside_schema = tmp_path / 'outside.schema.json'
    outside_schema.write_text(
        json.dumps({'type': 'object', 'additionalProperties': True}) + '\n',
        encoding='utf-8',
    )
    link = root / 'linked.schema.json'
    link.symlink_to(outside_schema)

    with pytest.raises(JsonSchemaValidationError, match='external schema path escapes root'):
        validate_artifact({}, 'linked.schema.json', root=root, allow_external_schema_refs=True)


def test_external_schema_ref_opt_in_does_not_fallback_to_repo_root(tmp_path: Path) -> None:
    with pytest.raises(JsonSchemaValidationError, match='schema file not found'):
        load_json_schema('pyproject.toml', root=tmp_path, allow_external_schema_refs=True)


def test_cli_explicit_schema_path_remains_operator_opt_in(tmp_path: Path) -> None:
    schema_path = tmp_path / 'custom.schema.json'
    value_path = tmp_path / 'value.json'
    schema_path.write_text(
        json.dumps(
            {
                'type': 'object',
                'required': ['custom'],
                'properties': {'custom': {'const': True}},
                'additionalProperties': False,
            }
        )
        + '\n',
        encoding='utf-8',
    )
    value_path.write_text(json.dumps({'custom': True}) + '\n', encoding='utf-8')

    proc = subprocess.run(
        [
            sys.executable,
            '-m',
            'sclite.cli',
            'validate-artifact',
            '--schema',
            str(schema_path),
            str(value_path),
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith('security_contract_artifact_ok:')
