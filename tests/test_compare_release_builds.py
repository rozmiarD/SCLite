from __future__ import annotations

import io
import shutil
import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts.compare_release_builds import compare_release_builds


def _build(directory: Path, *, wheel_payload: bytes = b"wheel", include_review: bool = False) -> None:
    directory.mkdir()
    wheel = directory / "sclite_core-2.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("sclite/__init__.py", wheel_payload)
        if include_review:
            archive.writestr("security/EXTERNAL_REVIEW.json", b"{}")
    sdist = directory / "sclite_core-2.0.0.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        payload = b"source"
        info = tarfile.TarInfo("sclite_core-2.0.0/sclite/__init__.py")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))


def test_compare_release_builds_accepts_identical_artifacts(tmp_path: Path) -> None:
    reviewed = tmp_path / "reviewed"
    published = tmp_path / "published"
    _build(reviewed)
    shutil.copytree(reviewed, published)
    compare_release_builds(reviewed, published)


def test_compare_release_builds_rejects_changed_bytes(tmp_path: Path) -> None:
    reviewed = tmp_path / "reviewed"
    published = tmp_path / "published"
    _build(reviewed)
    _build(published, wheel_payload=b"changed")
    with pytest.raises(ValueError, match="artifact bytes differ"):
        compare_release_builds(reviewed, published)


def test_compare_release_builds_rejects_packaged_review_record(tmp_path: Path) -> None:
    reviewed = tmp_path / "reviewed"
    published = tmp_path / "published"
    _build(reviewed, include_review=True)
    shutil.copytree(reviewed, published)
    with pytest.raises(ValueError, match="external review record is packaged"):
        compare_release_builds(reviewed, published)
