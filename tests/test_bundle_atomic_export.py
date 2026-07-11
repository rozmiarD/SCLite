from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import sclite.bundles as bundles
from sclite.bundles import (
    REVIEW_BUNDLE_REQUIRED_FILES,
    ReviewBundleError,
    materialize_review_bundle,
    validate_review_bundle_shape,
)


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_BUNDLE = ROOT / 'examples' / 'review-bundle'
GOVENGINE_BUNDLE = ROOT / 'examples' / 'govengine-integration'


def _source_artifacts() -> dict[str, dict]:
    return {
        role: json.loads((GOVENGINE_BUNDLE / filename).read_text(encoding='utf-8'))
        for role, filename in REVIEW_BUNDLE_REQUIRED_FILES.items()
    }


def _copy_public_bundle(tmp_path: Path) -> Path:
    target = tmp_path / 'bundle'
    shutil.copytree(PUBLIC_BUNDLE, target)
    return target


def _materialize(target: Path, **kwargs: object) -> dict:
    return materialize_review_bundle(
        target,
        _source_artifacts(),
        chain_id='atomic-export-test',
        created_at='2026-07-10T17:00:00+00:00',
        generated_at='2026-07-10T17:00:00+00:00',
        **kwargs,
    )


def test_public_export_inventory_accepts_only_closed_world_fixture() -> None:
    shape = validate_review_bundle_shape(PUBLIC_BUNDLE, mode='public_export')

    assert shape['status'] == 'passed'
    assert shape['mode'] == 'public_export'
    assert shape['inventory']['extras'] == []
    assert shape['inventory']['directories'] == []
    assert shape['inventory']['symlinks'] == []
    assert shape['inventory']['special_files'] == []


def test_local_review_reports_known_unbound_sidecars_without_rejecting() -> None:
    shape = validate_review_bundle_shape(GOVENGINE_BUNDLE, mode='local_review')

    assert shape['status'] == 'passed'
    assert shape['inventory']['extras'] == ['carrier_profile_ref.json', 'trust_profile_ref.json']
    with pytest.raises(ReviewBundleError, match='public export inventory is not closed-world'):
        validate_review_bundle_shape(GOVENGINE_BUNDLE, mode='public_export')


@pytest.mark.parametrize(
    'relative_path',
    [
        '.hidden-secret',
        'README.MD',
        'zażółć.json',
        'nested/private.json',
    ],
)
def test_public_export_rejects_hidden_case_unicode_and_nested_extras(
    tmp_path: Path,
    relative_path: str,
) -> None:
    bundle = _copy_public_bundle(tmp_path)
    extra = bundle / relative_path
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_text('private', encoding='utf-8')

    with pytest.raises(ReviewBundleError, match='public export inventory is not closed-world'):
        validate_review_bundle_shape(bundle, mode='public_export')


def test_public_export_rejects_symlink_and_local_review_reports_it(tmp_path: Path) -> None:
    bundle = _copy_public_bundle(tmp_path)
    outside = tmp_path / 'outside.txt'
    outside.write_text('private', encoding='utf-8')
    (bundle / 'linked-private').symlink_to(outside)

    local_shape = validate_review_bundle_shape(bundle, mode='local_review')
    assert local_shape['inventory']['symlinks'] == ['linked-private']
    with pytest.raises(ReviewBundleError, match='symlinks=linked-private'):
        validate_review_bundle_shape(bundle, mode='public_export')


@pytest.mark.skipif(not hasattr(os, 'mkfifo'), reason='FIFO creation is unavailable')
def test_public_export_rejects_special_file(tmp_path: Path) -> None:
    bundle = _copy_public_bundle(tmp_path)
    os.mkfifo(bundle / 'private.pipe')

    with pytest.raises(ReviewBundleError, match='special_files=private.pipe'):
        validate_review_bundle_shape(bundle, mode='public_export')


def test_public_export_rejects_hardlinked_file(tmp_path: Path) -> None:
    bundle = _copy_public_bundle(tmp_path)
    original = bundle / '01_intent_contract.json'
    outside = tmp_path / 'outside.json'
    original.replace(outside)
    os.link(outside, original)
    with pytest.raises(ReviewBundleError, match='hardlinks=01_intent_contract.json'):
        validate_review_bundle_shape(bundle, mode='public_export')


def test_materialization_publishes_complete_closed_world_bundle(tmp_path: Path) -> None:
    target = tmp_path / 'published'

    record = _materialize(target)
    shape = validate_review_bundle_shape(target, mode='public_export')

    assert record['verdict'] == 'pass'
    assert shape['inventory']['extras'] == []
    assert sorted(shape['inventory']['files']) == [
        '01_intent_contract.json',
        '02_policy_decision.json',
        '03_execution_contract.json',
        '04_execution_ticket.json',
        '05_execution_receipt.json',
        '06_evidence_contract.json',
        'REVIEW.md',
        'artifact_chain_manifest.json',
        'verification_receipt.json',
    ]
    assert not list(tmp_path.glob('.published.stage-*'))


def test_existing_target_requires_explicit_overwrite_and_stays_unchanged(
    tmp_path: Path,
) -> None:
    target = tmp_path / 'published'
    target.mkdir()
    marker = target / 'existing.txt'
    marker.write_text('original', encoding='utf-8')

    with pytest.raises(ReviewBundleError, match='pass overwrite=True'):
        _materialize(target)

    assert marker.read_text(encoding='utf-8') == 'original'


def test_explicit_overwrite_replaces_complete_target(tmp_path: Path) -> None:
    target = tmp_path / 'published'
    target.mkdir()
    (target / 'existing.txt').write_text('original', encoding='utf-8')

    _materialize(target, overwrite=True)

    assert not (target / 'existing.txt').exists()
    validate_review_bundle_shape(target, mode='public_export')
    assert not list(tmp_path.glob('.published.previous-*'))


def test_write_failure_leaves_existing_target_complete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / 'published'
    target.mkdir()
    marker = target / 'existing.txt'
    marker.write_text('original', encoding='utf-8')

    def fail_write(_path: Path, _payload: str) -> None:
        raise OSError('injected write failure')

    monkeypatch.setattr(bundles, '_write_text_fsynced', fail_write)
    with pytest.raises(OSError, match='injected write failure'):
        _materialize(target, overwrite=True)

    assert marker.read_text(encoding='utf-8') == 'original'
    assert not list(tmp_path.glob('.published.stage-*'))


def test_verification_failure_leaves_target_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / 'published'
    original_validate = bundles.validate_review_bundle_shape

    def fail_stage(path: Path | str, **kwargs: object) -> dict:
        if Path(path).name.startswith('.published.stage-'):
            raise ReviewBundleError('injected verification failure')
        return original_validate(path, **kwargs)

    monkeypatch.setattr(bundles, 'validate_review_bundle_shape', fail_stage)
    with pytest.raises(ReviewBundleError, match='injected verification failure'):
        _materialize(target)

    assert not target.exists()
    assert not list(tmp_path.glob('.published.stage-*'))


def test_publish_failure_rolls_back_existing_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / 'published'
    target.mkdir()
    marker = target / 'existing.txt'
    marker.write_text('original', encoding='utf-8')
    original_rename = bundles.os.rename

    def fail_stage_publish(source: Path | str, destination: Path | str) -> None:
        source_path = Path(source)
        destination_path = Path(destination)
        if source_path.name.startswith('.published.stage-') and destination_path == target:
            raise OSError('injected publish failure')
        original_rename(source, destination)

    monkeypatch.setattr(bundles.os, 'rename', fail_stage_publish)
    with pytest.raises(ReviewBundleError, match='atomic publish failed'):
        _materialize(target, overwrite=True)

    assert marker.read_text(encoding='utf-8') == 'original'
    assert not list(tmp_path.glob('.published.previous-*'))


def test_concurrent_creator_is_preserved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / 'published'
    original_publish = bundles._publish_stage

    def create_then_publish(stage: Path, destination: Path, *, overwrite: bool) -> None:
        destination.mkdir()
        (destination / 'concurrent.txt').write_text('creator', encoding='utf-8')
        original_publish(stage, destination, overwrite=overwrite)

    monkeypatch.setattr(bundles, '_publish_stage', create_then_publish)
    with pytest.raises(ReviewBundleError, match='pass overwrite=True'):
        _materialize(target)

    assert (target / 'concurrent.txt').read_text(encoding='utf-8') == 'creator'
    assert not list(tmp_path.glob('.published.stage-*'))


def test_export_cli_is_public_export_by_default_with_explicit_local_escape_hatch() -> None:
    public_result = subprocess.run(
        [sys.executable, '-m', 'sclite.kernel_cli', 'export-review-bundle', str(GOVENGINE_BUNDLE)],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    local_result = subprocess.run(
        [
            sys.executable,
            '-m',
            'sclite.kernel_cli',
            'export-review-bundle',
            str(GOVENGINE_BUNDLE),
            '--mode',
            'local_review',
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )

    assert public_result.returncode == 1
    assert 'input_validation_failed' in public_result.stderr
    assert local_result.returncode == 0, local_result.stderr
    assert local_result.stdout.startswith('# SCLite Review Record')


def test_public_export_failure_does_not_emit_absolute_path(tmp_path: Path) -> None:
    bundle = _copy_public_bundle(tmp_path)
    (bundle / '01_intent_contract.json').write_text('{"broken":', encoding='utf-8')
    result = subprocess.run(
        [sys.executable, '-m', 'sclite.kernel_cli', 'export-review-bundle', str(bundle)],
        cwd=str(ROOT), text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0
    assert str(bundle) not in result.stdout
    assert 'artifact_json_invalid' in result.stdout
