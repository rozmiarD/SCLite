#!/usr/bin/env python3
"""Validate the exact immutable description in one wheel and one sdist."""
from __future__ import annotations

import argparse
import re
import sys
import tarfile
import tomllib
import zipfile
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import NamedTuple


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_HEADERS = ("Name", "Version", "Description-Content-Type")


class MetadataValidationError(ValueError):
    """A release metadata invariant did not hold."""


class DistributionMetadata(NamedTuple):
    name: str
    version: str
    description_content_type: str
    description: bytes


def _project() -> dict[str, object]:
    with (ROOT / "pyproject.toml").open("rb") as source:
        return tomllib.load(source)["project"]


def _single_exact_member(names: list[str], *, kind: str, expected: str) -> str:
    matches = [name for name in names if name == expected]
    if len(matches) != 1:
        raise MetadataValidationError(f"{kind}:exact_member_count:{len(matches)}")
    return matches[0]


def _zip_regular(info: zipfile.ZipInfo) -> bool:
    mode = info.external_attr >> 16
    return not mode or (mode & 0o170000) in (0, 0o100000)


def _wheel_metadata_bytes(path: Path, *, root: str) -> bytes:
    expected = f"{root}.dist-info/METADATA"
    try:
        with zipfile.ZipFile(path) as archive:
            member = _single_exact_member(
                [info.filename for info in archive.infolist()],
                kind="wheel_metadata",
                expected=expected,
            )
            info = archive.getinfo(member)
            if not _zip_regular(info):
                raise MetadataValidationError("wheel_metadata:not_regular")
            return archive.read(member)
    except (OSError, zipfile.BadZipFile, KeyError) as error:
        raise MetadataValidationError(f"wheel:unreadable:{error}") from error


def _sdist_metadata_bytes(path: Path, *, root: str) -> bytes:
    expected = f"{root}/PKG-INFO"
    try:
        with tarfile.open(path, "r:gz") as archive:
            member = _single_exact_member(
                [item.name for item in archive.getmembers()],
                kind="sdist_root_pkg_info",
                expected=expected,
            )
            info = archive.getmember(member)
            if not info.isfile():
                raise MetadataValidationError("sdist_root_pkg_info:not_regular")
            extracted = archive.extractfile(info)
            if extracted is None:
                raise MetadataValidationError("sdist:pkg_info_unreadable")
            return extracted.read()
    except (OSError, tarfile.TarError) as error:
        raise MetadataValidationError(f"sdist:unreadable:{error}") from error


def _parse_metadata(raw: bytes, *, kind: str) -> DistributionMetadata:
    message = BytesParser(policy=policy.default).parsebytes(raw)
    if message.defects or message.is_multipart():
        raise MetadataValidationError(f"{kind}:invalid_metadata")
    values: dict[str, str] = {}
    for header in REQUIRED_HEADERS:
        occurrences = message.get_all(header, [])
        if len(occurrences) != 1 or not occurrences[0].strip():
            raise MetadataValidationError(f"{kind}:{header}:count:{len(occurrences)}")
        values[header] = occurrences[0].strip()
    separators = (
        (raw.find(b"\r\n\r\n"), 4),
        (raw.find(b"\n\n"), 2),
    )
    candidates = [(offset, length) for offset, length in separators if offset >= 0]
    if not candidates:
        raise MetadataValidationError(f"{kind}:missing_header_body_separator")
    offset, length = min(candidates)
    return DistributionMetadata(
        name=values["Name"],
        version=values["Version"],
        description_content_type=values["Description-Content-Type"],
        description=raw[offset + length:],
    )


def validate_distribution_metadata(*, wheel: Path, sdist: Path) -> None:
    project = _project()
    name = str(project["name"])
    version = str(project["version"])
    readme = project.get("readme")
    if readme != "PYPI_LONG_DESCRIPTION.md":
        raise MetadataValidationError(f"project_readme:{readme!r}")
    root = f"{re.sub(r'[-_.]+', '_', name)}-{version}"
    try:
        source_description = (ROOT / str(readme)).read_bytes()
    except OSError as error:
        raise MetadataValidationError(f"source_description:unreadable:{error}") from error

    metadata = {
        "wheel": _parse_metadata(_wheel_metadata_bytes(wheel, root=root), kind="wheel"),
        "sdist": _parse_metadata(_sdist_metadata_bytes(sdist, root=root), kind="sdist"),
    }
    for kind, parsed in metadata.items():
        if parsed.name != name:
            raise MetadataValidationError(f"{kind}:name:{parsed.name}!={name}")
        if parsed.version != version:
            raise MetadataValidationError(f"{kind}:version:{parsed.version}!={version}")
        if parsed.description_content_type != "text/markdown":
            raise MetadataValidationError(
                f"{kind}:description_content_type:{parsed.description_content_type}!=text/markdown"
            )
        if parsed.description != source_description:
            raise MetadataValidationError(f"{kind}:description_mismatch:source")
    if metadata["wheel"].description != metadata["sdist"].description:
        raise MetadataValidationError("wheel_sdist:description_mismatch")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--sdist", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        validate_distribution_metadata(wheel=args.wheel, sdist=args.sdist)
    except MetadataValidationError as error:
        print(f"distribution_metadata_invalid:{error}", file=sys.stderr)
        return 1
    project = _project()
    print(f"distribution_metadata_ok:{project['name']}=={project['version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
