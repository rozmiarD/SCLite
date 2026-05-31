from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping

from ._json import load_json_object
from .integrity import build_artifact_chain_manifest
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


class ReviewBundleError(ValueError):
    """Raised when a review bundle is missing canonical files or fails review."""


def _load_json_object(path: Path) -> Dict[str, Any]:
    return load_json_object(path, error_cls=ReviewBundleError)


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


def validate_review_bundle_shape(bundle_dir: Path | str) -> Dict[str, Any]:
    """Validate canonical review-bundle file placement without running tools."""
    base = _bundle_path(bundle_dir)
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

    manifest = _load_json_object(manifest_path)
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
        'bundle_dir': str(base),
        'files': files,
        'manifest': REVIEW_BUNDLE_MANIFEST_FILE,
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
) -> Dict[str, Any]:
    """Review a canonical SCLite review bundle and return a ReviewRecord."""
    base = _bundle_path(bundle_dir)
    shape = validate_review_bundle_shape(base)
    try:
        record = build_review_record_from_manifest(
            base / REVIEW_BUNDLE_MANIFEST_FILE,
            root=base,
            strict_jsonschema=strict_jsonschema,
            generated_at=generated_at,
        )
    except ReviewRecordError as exc:
        raise ReviewBundleError(str(exc)) from exc
    return _as_bundle_review_record(record, shape['files'])


def materialize_review_bundle(
    bundle_dir: Path | str,
    artifacts_by_role: Mapping[str, Mapping[str, Any]],
    *,
    chain_id: str = 'sclite-review-bundle',
    created_at: str | None = None,
    generated_at: str | None = None,
    strict_jsonschema: bool = False,
) -> Dict[str, Any]:
    """Write and review a canonical local bundle from lifecycle artifacts.

    This is artifact packaging only. It does not execute a runtime, authorize
    side effects, decide signer trust, or publish the resulting directory.
    """
    missing = [role for role in REVIEW_BUNDLE_REQUIRED_FILES if role not in artifacts_by_role]
    if missing:
        raise ReviewBundleError('missing lifecycle artifacts for review bundle: ' + ', '.join(missing))

    base = Path(bundle_dir).resolve()
    base.mkdir(parents=True, exist_ok=True)
    manifest_inputs: list[Dict[str, Any]] = []
    for role, filename in REVIEW_BUNDLE_REQUIRED_FILES.items():
        artifact = artifacts_by_role[role]
        if not isinstance(artifact, Mapping):
            raise ReviewBundleError(f'{role}: lifecycle artifact is not an object')
        path = base / filename
        _assert_inside(base, path)
        value = dict(artifact)
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        manifest_inputs.append({'role': role, 'path': filename, 'value': value})

    manifest = build_artifact_chain_manifest(
        manifest_inputs,
        chain_id=chain_id,
        **({'created_at': created_at} if created_at else {}),
    )
    (base / REVIEW_BUNDLE_MANIFEST_FILE).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + '\n',
        encoding='utf-8',
    )
    try:
        record = build_review_record_from_manifest(
            base / REVIEW_BUNDLE_MANIFEST_FILE,
            root=base,
            strict_jsonschema=strict_jsonschema,
            generated_at=generated_at,
        )
    except ReviewRecordError as exc:
        raise ReviewBundleError(str(exc)) from exc
    files = {**REVIEW_BUNDLE_REQUIRED_FILES, **REVIEW_BUNDLE_SIDECAR_FILES}
    record = _as_bundle_review_record(record, files)
    (base / REVIEW_BUNDLE_RECEIPT_FILE).write_text(
        json.dumps(record, indent=2, sort_keys=True) + '\n',
        encoding='utf-8',
    )
    (base / REVIEW_BUNDLE_MARKDOWN_FILE).write_text(review_record_markdown(record), encoding='utf-8')
    validate_review_bundle_shape(base)
    return record


def export_review_bundle_markdown(record: Mapping[str, Any]) -> str:
    """Return reviewer-friendly Markdown for a ReviewRecord."""
    return review_record_markdown(record)


def review_bundle_summary(record: Mapping[str, Any]) -> str:
    summary = record.get('summary') if isinstance(record.get('summary'), Mapping) else {}
    return (
        f"review_bundle:{record.get('verdict')}:{summary.get('artifact_count')}:{summary.get('root_chain_digest')}"
    )
