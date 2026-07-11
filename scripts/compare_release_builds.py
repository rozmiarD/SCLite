from __future__ import annotations

import argparse
import hashlib
import tarfile
import zipfile
from pathlib import Path


def _artifacts(directory: Path) -> dict[str, Path]:
    files = sorted(path for path in directory.iterdir() if path.is_file())
    wheels = [path for path in files if path.suffix == ".whl"]
    sdists = [path for path in files if path.name.endswith(".tar.gz")]
    if len(wheels) != 1 or len(sdists) != 1 or len(files) != 2:
        raise ValueError("release build must contain exactly one wheel and one sdist")
    return {path.name: path for path in files}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_review_record_excluded(path: Path) -> None:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
    else:
        with tarfile.open(path, "r:gz") as archive:
            names = archive.getnames()
    if any(name.endswith("security/EXTERNAL_REVIEW.json") for name in names):
        raise ValueError(f"external review record is packaged in {path.name}")


def compare_release_builds(reviewed: Path, published: Path) -> None:
    reviewed_artifacts = _artifacts(reviewed)
    published_artifacts = _artifacts(published)
    if reviewed_artifacts.keys() != published_artifacts.keys():
        raise ValueError("reviewed and published artifact names differ")
    for name, reviewed_path in reviewed_artifacts.items():
        published_path = published_artifacts[name]
        _assert_review_record_excluded(reviewed_path)
        _assert_review_record_excluded(published_path)
        reviewed_digest = _digest(reviewed_path)
        published_digest = _digest(published_path)
        if reviewed_digest != published_digest:
            raise ValueError(f"reviewed and published artifact bytes differ: {name}")
        print(f"release_build_match:{name}:{published_digest}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewed", type=Path, required=True)
    parser.add_argument("--published", type=Path, required=True)
    args = parser.parse_args()
    try:
        compare_release_builds(args.reviewed, args.published)
    except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as exc:
        print(f"release_build_comparison_failed:{exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
