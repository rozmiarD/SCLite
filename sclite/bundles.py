from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, Literal, Mapping

from ._json import VerificationLimits, load_json_object
from .errors import SCLiteValidationError
from .integrity import build_artifact_chain_manifest
from .json_types import json_mapping
from .review import ReviewRecordError, build_review_record_from_manifest, review_record_markdown

REVIEW_BUNDLE_REQUIRED_FILES = {
    'intent_contract': '01_intent_contract.json',
    'policy_decision': '02_policy_decision.json',
    'execution_contract': '03_execution_contract.json',
    'execution_ticket': '04_execution_ticket.json',
    'execution_receipt': '05_execution_receipt.json',
    'evidence_contract': '06_evidence_contract.json',
}
REVIEW_BUNDLE_MANIFEST_FILE = 'artifact_chain_manifest.json'
REVIEW_BUNDLE_MARKDOWN_FILE = 'REVIEW.md'
REVIEW_BUNDLE_RECEIPT_FILE = 'verification_receipt.json'
REVIEW_BUNDLE_SIDECAR_FILES = {
    'review_markdown': REVIEW_BUNDLE_MARKDOWN_FILE,
    'verification_receipt': REVIEW_BUNDLE_RECEIPT_FILE,
}
ReviewBundleMode = Literal['public_export', 'local_review']
REVIEW_BUNDLE_PUBLIC_OPTIONAL_FILES = frozenset({'README.md'})


class ReviewBundleError(SCLiteValidationError):
    """Raised when a review bundle is missing canonical files or fails review."""

    default_code = 'review_bundle_failed'


def _load_json_object(
    path: Path,
    *,
    verification_limits: VerificationLimits | None = None,
) -> Dict[str, Any]:
    return load_json_object(path, error_cls=ReviewBundleError, limits=verification_limits)


def _bundle_path(bundle_dir: Path | str) -> Path:
    path = Path(bundle_dir).resolve()
    if not path.is_dir():
        raise ReviewBundleError(f'{path}: review bundle directory not found')
    return path


def _assert_inside(base: Path, path: Path) -> None:
    try:
        path.resolve().relative_to(base.resolve())
    except ValueError as exc:
        raise ReviewBundleError(f'{path}: path escapes review bundle') from exc


def _recursive_inventory(base: Path, *, limits: VerificationLimits) -> Dict[str, list[str]]:
    inventory: Dict[str, list[str]] = {
        'files': [],
        'directories': [],
        'symlinks': [],
        'special_files': [],
        'hardlinks': [],
    }
    pending = [(base, 0)]
    entry_count = 0
    path_bytes = 0
    try:
        while pending:
            current, depth = pending.pop()
            if depth > limits.max_directory_depth:
                raise ReviewBundleError('review bundle inventory exceeds max_directory_depth')
            with os.scandir(current) as entries:
                for entry in entries:
                    path = Path(entry.path)
                    relative = path.relative_to(base).as_posix()
                    entry_count += 1
                    path_bytes += len(relative.encode('utf-8'))
                    if entry_count > limits.max_inventory_entries:
                        raise ReviewBundleError('review bundle inventory exceeds max_inventory_entries')
                    if path_bytes > limits.max_path_bytes:
                        raise ReviewBundleError('review bundle inventory exceeds max_path_bytes')
                    if entry.is_symlink():
                        inventory['symlinks'].append(relative)
                    elif entry.is_file(follow_symlinks=False):
                        if entry.stat(follow_symlinks=False).st_nlink != 1:
                            inventory['hardlinks'].append(relative)
                        else:
                            inventory['files'].append(relative)
                    elif entry.is_dir(follow_symlinks=False):
                        inventory['directories'].append(relative)
                        pending.append((path, depth + 1))
                    else:
                        inventory['special_files'].append(relative)
    except OSError as exc:
        raise ReviewBundleError(f'{base}: cannot inventory review bundle: {exc}') from exc
    for values in inventory.values():
        values.sort()
    return inventory


def _public_inventory_errors(inventory: Mapping[str, list[str]]) -> list[str]:
    required_files = {
        *REVIEW_BUNDLE_REQUIRED_FILES.values(),
        REVIEW_BUNDLE_MANIFEST_FILE,
        *REVIEW_BUNDLE_SIDECAR_FILES.values(),
    }
    allowed_files = required_files | set(REVIEW_BUNDLE_PUBLIC_OPTIONAL_FILES)
    extras = sorted(set(inventory['files']) - allowed_files)
    errors = []
    if extras:
        errors.append('extras=' + ','.join(extras))
    for category in ('directories', 'symlinks', 'special_files', 'hardlinks'):
        if inventory[category]:
            errors.append(category + '=' + ','.join(inventory[category]))
    return errors


def validate_review_bundle_shape(
    bundle_dir: Path | str,
    *,
    mode: ReviewBundleMode = 'local_review',
    verification_limits: VerificationLimits | None = None,
) -> Dict[str, Any]:
    """Validate canonical review-bundle file placement without running tools."""
    if mode not in {'public_export', 'local_review'}:
        raise ReviewBundleError(f'unsupported review bundle mode: {mode}')
    base = _bundle_path(bundle_dir)
    limits = verification_limits or VerificationLimits()
    inventory = _recursive_inventory(base, limits=limits)
    public_inventory_errors = _public_inventory_errors(inventory)
    if mode == 'public_export' and public_inventory_errors:
        raise ReviewBundleError(
            'public export inventory is not closed-world: ' + '; '.join(public_inventory_errors)
        )
    missing = []
    files: Dict[str, str] = {}
    for role, filename in REVIEW_BUNDLE_REQUIRED_FILES.items():
        path = base / filename
        _assert_inside(base, path)
        files[role] = filename
        if not path.is_file():
            missing.append(filename)
    manifest_path = base / REVIEW_BUNDLE_MANIFEST_FILE
    _assert_inside(base, manifest_path)
    if not manifest_path.is_file():
        missing.append(REVIEW_BUNDLE_MANIFEST_FILE)
    for role, filename in REVIEW_BUNDLE_SIDECAR_FILES.items():
        path = base / filename
        _assert_inside(base, path)
        files[role] = filename
        if not path.is_file():
            missing.append(filename)
    if missing:
        raise ReviewBundleError('missing review bundle files: ' + ', '.join(missing))

    manifest = _load_json_object(manifest_path, verification_limits=verification_limits)
    entries = manifest.get('entries')
    if not isinstance(entries, list):
        raise ReviewBundleError('artifact_chain_manifest.json has no entries array')
    paths_by_role = {str(entry.get('role') or ''): str(entry.get('path') or '') for entry in entries if isinstance(entry, Mapping)}
    path_errors = []
    for role, filename in REVIEW_BUNDLE_REQUIRED_FILES.items():
        if paths_by_role.get(role) != filename:
            path_errors.append(f'{role}:{paths_by_role.get(role) or "missing"}!={filename}')
    if path_errors:
        raise ReviewBundleError('manifest paths do not match canonical review bundle shape: ' + '; '.join(path_errors))
    return {
        'status': 'passed',
        'mode': mode,
        'bundle_dir': '.',
        'files': files,
        'manifest': REVIEW_BUNDLE_MANIFEST_FILE,
        'inventory': {
            **inventory,
            'extras': sorted(
                set(inventory['files'])
                - {
                    *REVIEW_BUNDLE_REQUIRED_FILES.values(),
                    REVIEW_BUNDLE_MANIFEST_FILE,
                    *REVIEW_BUNDLE_SIDECAR_FILES.values(),
                    *REVIEW_BUNDLE_PUBLIC_OPTIONAL_FILES,
                }
            ),
        },
    }


def _as_bundle_review_record(record: Dict[str, Any], files: Mapping[str, str]) -> Dict[str, Any]:
    record['review_profile'] = 'sclite-review-bundle-v0.1'
    record['source_manifest'] = REVIEW_BUNDLE_MANIFEST_FILE
    record['summary']['review_bundle_shape'] = 'canonical-v0.1'
    record['summary']['review_bundle_files'] = dict(files)
    return record


def review_bundle(
    bundle_dir: Path | str,
    *,
    strict_jsonschema: bool = False,
    generated_at: str | None = None,
    mode: ReviewBundleMode = 'local_review',
    verification_limits: VerificationLimits | None = None,
) -> Dict[str, Any]:
    """Review a canonical SCLite review bundle and return a ReviewRecord."""
    base = _bundle_path(bundle_dir)
    shape = validate_review_bundle_shape(
        base,
        mode=mode,
        verification_limits=verification_limits,
    )
    try:
        record = build_review_record_from_manifest(
            base / REVIEW_BUNDLE_MANIFEST_FILE,
            root=base,
            strict_jsonschema=strict_jsonschema,
            generated_at=generated_at,
            verification_limits=verification_limits,
        )
    except ReviewRecordError as exc:
        raise ReviewBundleError(str(exc)) from exc
    return _as_bundle_review_record(record, shape['files'])


def _write_text_fsynced(path: Path, payload: str) -> None:
    with path.open('w', encoding='utf-8', newline='') as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish_stage(stage: Path, target: Path, *, overwrite: bool) -> None:
    if target.is_symlink():
        raise ReviewBundleError(f'{target}: refusing to replace symlink target')
    if target.exists() and not target.is_dir():
        raise ReviewBundleError(f'{target}: target exists and is not a directory')
    if target.exists() and not overwrite:
        raise ReviewBundleError(f'{target}: target exists; pass overwrite=True to replace it')

    backup: Path | None = None
    if target.exists():
        backup = target.parent / f'.{target.name}.previous-{uuid.uuid4().hex}'
        os.rename(target, backup)
    try:
        os.rename(stage, target)
    except OSError as exc:
        if backup is not None and backup.exists() and not target.exists():
            os.rename(backup, target)
        raise ReviewBundleError(f'{target}: atomic publish failed: {exc}') from exc

    _fsync_directory(target.parent)
    if backup is not None:
        try:
            shutil.rmtree(backup)
        except OSError as exc:
            raise ReviewBundleError(
                f'{target}: published successfully but previous target cleanup failed: {exc}'
            ) from exc


def materialize_review_bundle(
    bundle_dir: Path | str,
    artifacts_by_role: Mapping[str, Mapping[str, Any]],
    *,
    chain_id: str = 'sclite-review-bundle',
    created_at: str | None = None,
    generated_at: str | None = None,
    strict_jsonschema: bool = False,
    mode: ReviewBundleMode = 'public_export',
    overwrite: bool = False,
    verification_limits: VerificationLimits | None = None,
) -> Dict[str, Any]:
    """Write and review a canonical local bundle from lifecycle artifacts.

    This is artifact packaging only. It does not execute a runtime, authorize
    side effects, decide signer trust, or publish the resulting directory.
    """
    missing = [role for role in REVIEW_BUNDLE_REQUIRED_FILES if role not in artifacts_by_role]
    if missing:
        raise ReviewBundleError('missing lifecycle artifacts for review bundle: ' + ', '.join(missing))

    if mode not in {'public_export', 'local_review'}:
        raise ReviewBundleError(f'unsupported review bundle mode: {mode}')
    base = Path(bundle_dir).resolve()
    base.parent.mkdir(parents=True, exist_ok=True)
    if base.is_symlink():
        raise ReviewBundleError(f'{base}: refusing to materialize through symlink target')
    if base.exists() and not overwrite:
        raise ReviewBundleError(f'{base}: target exists; pass overwrite=True to replace it')
    stage = Path(tempfile.mkdtemp(prefix=f'.{base.name}.stage-', dir=base.parent))
    try:
        manifest_inputs: list[Dict[str, Any]] = []
        for role, filename in REVIEW_BUNDLE_REQUIRED_FILES.items():
            artifact = artifacts_by_role[role]
            if not isinstance(artifact, Mapping):
                raise ReviewBundleError(f'{role}: lifecycle artifact is not an object')
            path = stage / filename
            _assert_inside(stage, path)
            value = dict(artifact)
            _write_text_fsynced(path, json.dumps(value, indent=2, sort_keys=True) + '\n')
            manifest_inputs.append({'role': role, 'path': filename, 'value': value})

        manifest = build_artifact_chain_manifest(
            manifest_inputs,
            chain_id=chain_id,
            **({'created_at': created_at} if created_at else {}),
        )
        _write_text_fsynced(
            stage / REVIEW_BUNDLE_MANIFEST_FILE,
            json.dumps(manifest, indent=2, sort_keys=True) + '\n',
        )
        record = build_review_record_from_manifest(
            stage / REVIEW_BUNDLE_MANIFEST_FILE,
            root=stage,
            strict_jsonschema=strict_jsonschema,
            generated_at=generated_at,
            verification_limits=verification_limits,
        )
        files = {**REVIEW_BUNDLE_REQUIRED_FILES, **REVIEW_BUNDLE_SIDECAR_FILES}
        record = _as_bundle_review_record(record, files)
        _write_text_fsynced(
            stage / REVIEW_BUNDLE_RECEIPT_FILE,
            json.dumps(record, indent=2, sort_keys=True) + '\n',
        )
        _write_text_fsynced(stage / REVIEW_BUNDLE_MARKDOWN_FILE, review_record_markdown(record))
        validate_review_bundle_shape(
            stage,
            mode=mode,
            verification_limits=verification_limits,
        )
        _fsync_directory(stage)
        _publish_stage(stage, base, overwrite=overwrite)
        return record
    except ReviewRecordError as exc:
        raise ReviewBundleError(str(exc)) from exc
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)


def export_review_bundle_markdown(record: Mapping[str, Any]) -> str:
    """Return reviewer-friendly Markdown for a ReviewRecord."""
    return review_record_markdown(record)


def review_bundle_summary(record: Mapping[str, Any]) -> str:
    summary = json_mapping(record.get('summary'))
    return (
        f"review_bundle:{record.get('verdict')}:{summary.get('artifact_count')}:{summary.get('root_chain_digest')}"
    )
