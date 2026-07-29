#!/usr/bin/env python3
"""Fail closed when a release SBOM does not describe its exact product wheel."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from email.parser import BytesParser
from email.policy import default
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name


def _metadata_values(metadata: object, header: str) -> list[str]:
    values = metadata.get_all(header, [])
    if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        raise ValueError(f'wheel_metadata_{header.lower()}_invalid')
    return values


def _declared_extras(metadata: object) -> set[str]:
    extras = _metadata_values(metadata, 'Provides-Extra')
    normalized = [canonicalize_name(extra) for extra in extras]
    if len(normalized) != len(set(normalized)):
        raise ValueError('wheel_metadata_provides_extra_not_unique')
    return set(normalized)


def _validate_requires_dist(metadata: object, extras: set[str]) -> None:
    for value in _metadata_values(metadata, 'Requires-Dist'):
        try:
            requirement = Requirement(value)
        except InvalidRequirement as exc:
            raise ValueError(f'wheel_metadata_requires_dist_invalid:{value}') from exc
        marker = str(requirement.marker) if requirement.marker is not None else ''
        match = re.fullmatch(r'extra == "([^"]+)"', marker)
        if match is None:
            raise ValueError(f'wheel_metadata_requires_dist_not_extra_guarded:{value}')
        if canonicalize_name(match.group(1)) not in extras:
            raise ValueError(f'wheel_metadata_requires_dist_extra_undeclared:{value}')


def _wheel_metadata(wheel: Path) -> tuple[str, str]:
    with zipfile.ZipFile(wheel) as archive:
        metadata_members = [
            name for name in archive.namelist() if name.endswith('.dist-info/METADATA')
        ]
        if len(metadata_members) != 1:
            raise ValueError(f'wheel_metadata_members={len(metadata_members)}')
        metadata = BytesParser(policy=default).parsebytes(archive.read(metadata_members[0]))

    if metadata.defects:
        raise ValueError(f'wheel_metadata_parser_defects:{len(metadata.defects)}')
    names = _metadata_values(metadata, 'Name')
    versions = _metadata_values(metadata, 'Version')
    if len(names) != 1:
        raise ValueError(f'wheel_metadata_name_count:{len(names)}')
    if not names[0]:
        raise ValueError('wheel_metadata_name_missing')
    if len(versions) != 1:
        raise ValueError(f'wheel_metadata_version_count:{len(versions)}')
    if not versions[0]:
        raise ValueError('wheel_metadata_version_missing')
    _validate_requires_dist(metadata, _declared_extras(metadata))
    return names[0], versions[0]


def _metadata_tool_names(tools: object) -> set[str]:
    if isinstance(tools, dict):
        components = tools.get('components', [])
    elif isinstance(tools, list):
        components = tools
    else:
        return set()
    if not isinstance(components, list):
        return set()
    return {
        component['name']
        for component in components
        if isinstance(component, dict) and isinstance(component.get('name'), str)
    }


def _properties_contain_reproducible(properties: object) -> bool:
    if not isinstance(properties, list):
        return False
    return any(
        isinstance(property_, dict)
        and property_.get('name') == 'cdx:reproducible'
        and property_.get('value') == 'true'
        for property_ in properties
    )


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate_json_key:{key}')
        result[key] = value
    return result


def collect_errors(*, wheel: Path, sbom: Path) -> list[str]:
    errors: list[str] = []
    try:
        wheel_name, wheel_version = _wheel_metadata(wheel)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        return [f'wheel_metadata_invalid:{exc}']

    try:
        document = json.loads(
            sbom.read_text(encoding='utf-8'), object_pairs_hook=_reject_duplicate_json_keys
        )
    except (OSError, ValueError) as exc:
        return [f'sbom_invalid_json:{exc}']
    if not isinstance(document, dict):
        return ['sbom_document_not_object']

    metadata = document.get('metadata')
    if not isinstance(metadata, dict):
        return ['sbom_metadata_missing']
    component = metadata.get('component')
    if not isinstance(component, dict):
        return ['sbom_metadata_component_missing']

    if component.get('name') != wheel_name:
        errors.append(f'component_name_mismatch:{component.get("name")}!={wheel_name}')
    if component.get('version') != wheel_version:
        errors.append(f'component_version_mismatch:{component.get("version")}!={wheel_version}')
    if component.get('type') != 'library':
        errors.append(f'component_type_mismatch:{component.get("type")}!=library')
    if not _properties_contain_reproducible(metadata.get('properties')):
        errors.append('metadata_reproducible_missing_or_false')

    components = document.get('components', [])
    if not isinstance(components, list):
        errors.append('top_level_components_not_list')
        components = []
    elif components:
        errors.append(f'top_level_runtime_components_not_empty:{len(components)}')

    tool_names = _metadata_tool_names(metadata.get('tools'))
    for component_ in components:
        if isinstance(component_, dict) and component_.get('name') in tool_names:
            errors.append(f'generator_tool_leaked_into_components:{component_["name"]}')

    root_ref = component.get('bom-ref')
    dependencies = document.get('dependencies', [])
    if not isinstance(dependencies, list):
        errors.append('dependencies_not_list')
    elif not isinstance(root_ref, str) or not root_ref:
        errors.append('component_bom_ref_missing')
    else:
        if len(dependencies) != 1:
            errors.append(f'dependency_entry_count:{len(dependencies)}')
        elif not isinstance(dependencies[0], dict) or dependencies[0].get('ref') != root_ref:
            errors.append('root_dependency_entry_missing_or_orphaned')
        elif dependencies[0].get('dependsOn', []) != []:
            errors.append('root_unconditional_runtime_dependencies_not_empty')

    return errors


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--sbom', type=Path, required=True)
    args = parser.parse_args(argv)

    errors = collect_errors(wheel=args.wheel, sbom=args.sbom)
    if errors:
        for error in errors:
            print(f'product_sbom_invalid:{error}', file=sys.stderr)
        return 1

    wheel_name, wheel_version = _wheel_metadata(args.wheel)
    print(
        'product_sbom_ok:'
        f'{wheel_name}=={wheel_version}:wheel_sha256={_sha256(args.wheel)}'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
