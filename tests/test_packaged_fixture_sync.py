from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _relative_files(root: Path) -> set[Path]:
    return {
        path.relative_to(root)
        for path in root.rglob('*')
        if path.is_file() and path.name != '__init__.py'
    }


def test_packaged_schemas_match_source_schemas() -> None:
    source = ROOT / 'schemas'
    packaged = ROOT / 'sclite' / 'schemas'
    assert _relative_files(source) == _relative_files(packaged)
    for rel_path in sorted(_relative_files(source)):
        assert (packaged / rel_path).read_bytes() == (source / rel_path).read_bytes(), rel_path


def test_packaged_public_review_fixtures_match_source_fixtures() -> None:
    for fixture in ['review-bundle', 'govengine-integration', 'bad-review-bundle-cross-host']:
        source = ROOT / 'examples' / fixture
        packaged = ROOT / 'sclite' / 'examples' / fixture
        assert _relative_files(source) == _relative_files(packaged), fixture
        for rel_path in sorted(_relative_files(source)):
            assert (packaged / rel_path).read_bytes() == (source / rel_path).read_bytes(), f'{fixture}/{rel_path}'
