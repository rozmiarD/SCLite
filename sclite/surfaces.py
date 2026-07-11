from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence

from ._json import load_json_value
from .artifacts import build_artifact_hash
from .disclosure import (
    DisclosureStatus,
    build_disclosure_status,
    relative_public_path,
)


PUBLIC_VALIDATION_SURFACE_INDEX_ARTIFACT_TYPE = 'public_validation_surface_index'
PUBLIC_VALIDATION_SURFACE_INDEX_SCHEMA_VERSION = 'v0.2'
PUBLIC_SNAPSHOT_MANIFEST_ARTIFACT_TYPE = 'public_snapshot_manifest'
PUBLIC_SNAPSHOT_MANIFEST_SCHEMA_VERSION = 'v0.2'


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_public_validation_surface_index(*, generated_at: str | None = None) -> Dict[str, Any]:
    """Return the current public-safe SCLite lifecycle/review surface index.

    The index describes what a reviewer can validate locally. It does not claim
    live execution, authorization, or protocol adapter coverage.
    """
    surfaces = [
        {
            'surface_id': 'lifecycle_review_fixture',
            'path': 'examples/lifecycle-review/review_record.json',
            'kind': 'json_artifact',
            'purpose': 'Validate a static lifecycle review aggregate and its scope-fidelity result.',
            'schemas': ['review_record.v0.1', 'scope_fidelity_report.v0.2'],
            'commands': ['sclite review-lifecycle sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json --format json'],
            'disclosure': build_disclosure_status(status='operator_asserted'),
        },
        {
            'surface_id': 'review_bundle_fixture',
            'path': 'examples/review-bundle',
            'kind': 'review_bundle_directory',
            'purpose': 'Validate and export a canonical SCLite current lifecycle/review bundle.',
            'schemas': ['review_record.v0.1', 'artifact_chain_manifest.v0.2'],
            'commands': ['sclite review examples/review-bundle --format json', 'sclite export-review-bundle examples/review-bundle --format markdown'],
            'disclosure': build_disclosure_status(status='operator_asserted'),
        },
        {
            'surface_id': 'govengine_integration_fixture',
            'path': 'examples/govengine-integration',
            'kind': 'review_bundle_directory',
            'purpose': 'Validate the current downstream integration fixture for GovEngine consumption.',
            'schemas': ['review_record.v0.1', 'artifact_chain_manifest.v0.2', 'execution_ticket.v0.3', 'trust_profile_ref.v0.1', 'carrier_profile_ref.v0.1'],
            'commands': [
                'sclite review examples/govengine-integration --format json --fail-on review',
                'sclite verify-secure-bundle examples/govengine-integration --guard /path/to/kernel_guard_manifest.json',
                'sclite validate-trust-profile examples/govengine-integration/trust_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json',
                'sclite validate-carrier-profile examples/govengine-integration/carrier_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json',
            ],
            'disclosure': build_disclosure_status(status='operator_asserted'),
        },
        {
            'surface_id': 'local_admin_change_fixture',
            'path': 'examples/local-admin-change',
            'kind': 'review_bundle_directory',
            'purpose': 'Validate the current local-admin-change fixture as a non-security multi-runtime proof surface.',
            'schemas': ['review_record.v0.1', 'artifact_chain_manifest.v0.2', 'execution_ticket.v0.3'],
            'commands': ['sclite review examples/local-admin-change --format json --fail-on review'],
            'disclosure': build_disclosure_status(status='operator_asserted'),
        },
    ]
    return {
        'artifact_type': PUBLIC_VALIDATION_SURFACE_INDEX_ARTIFACT_TYPE,
        'schema_version': PUBLIC_VALIDATION_SURFACE_INDEX_SCHEMA_VERSION,
        'generated_at': generated_at or _utc_now(),
        'surfaces': surfaces,
        'summary': {
            'surface_count': len(surfaces),
        },
        'disclosure': build_disclosure_status(status='operator_asserted'),
        'public_safety': {
            'live_target_execution': False,
            'protocol_adapter_work': False,
            'public_push_authorized': False,
            'raw_live_evidence_included': False,
        },
        'non_claims': [
            'does_not_claim_live_vulnerability_evidence',
            'does_not_authorize_publication',
            'does_not_cover_protocol_adapter_execution',
        ],
    }


def build_public_snapshot_manifest(
    files: Sequence[Mapping[str, Any]],
    *,
    snapshot_name: str = 'sclite-public-snapshot',
    snapshot_version: str = 'v0.1',
    generated_at: str | None = None,
) -> Dict[str, Any]:
    """Build a public-safe snapshot manifest for already-selected artifacts.

    Each file entry may provide `path`, `artifact_type`, `schema`, and `value`.
    When `value` is present, a canonical SHA-256 hash descriptor is included.
    """
    normalized = []
    for item in files:
        requested_status = str(item.get('disclosure_status') or '')
        status: DisclosureStatus = (
            requested_status if requested_status else 'unknown'  # type: ignore[assignment]
        )
        disclosure = build_disclosure_status(
            status=status,
            checks=[str(value) for value in item.get('disclosure_checks', [])],
            policy=str(item.get('disclosure_policy') or ''),
        )
        entry: Dict[str, Any] = {
            'path': relative_public_path(str(item.get('path') or 'artifact.json')),
            'artifact_type': str(item.get('artifact_type') or ''),
            'schema': str(item.get('schema') or ''),
            'disclosure': disclosure,
        }
        if 'value' in item:
            entry['hash'] = build_artifact_hash(item['value'])
        normalized.append(entry)
    return {
        'artifact_type': PUBLIC_SNAPSHOT_MANIFEST_ARTIFACT_TYPE,
        'schema_version': PUBLIC_SNAPSHOT_MANIFEST_SCHEMA_VERSION,
        'snapshot_name': snapshot_name,
        'snapshot_version': snapshot_version,
        'generated_at': generated_at or _utc_now(),
        'files': normalized,
        'summary': {
            'file_count': len(normalized),
            'hashed_file_count': sum(1 for item in normalized if 'hash' in item),
        },
        'disclosure': build_disclosure_status(status='unknown'),
        'public_safety': {
            'live_target_execution': False,
            'protocol_adapter_work': False,
            'raw_live_evidence_included': False,
            'raw_stdout_stderr_included': False,
        },
        'non_claims': [
            'does_not_claim_live_vulnerability_evidence',
            'does_not_prove_artifact_provenance',
            'does_not_authorize_publication',
        ],
    }


def manifest_entries_from_paths(paths: Iterable[Path], *, schema: str = '') -> list[Dict[str, Any]]:
    """Load JSON files and return manifest file entries with hashable values."""
    entries: list[Dict[str, Any]] = []
    for path in paths:
        value = load_json_value(path, error_cls=ValueError)
        artifact_type = value.get('artifact_type') if isinstance(value, dict) else ''
        entries.append({
            'path': relative_public_path(path),
            'artifact_type': str(artifact_type or ''),
            'schema': schema,
            'disclosure_status': 'unknown',
            'value': value,
        })
    return entries
