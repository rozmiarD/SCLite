from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence

from .artifacts import build_artifact_hash


PUBLIC_VALIDATION_SURFACE_INDEX_ARTIFACT_TYPE = 'public_validation_surface_index'
PUBLIC_VALIDATION_SURFACE_INDEX_SCHEMA_VERSION = 'v0.1'
PUBLIC_SNAPSHOT_MANIFEST_ARTIFACT_TYPE = 'public_snapshot_manifest'
PUBLIC_SNAPSHOT_MANIFEST_SCHEMA_VERSION = 'v0.1'


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_public_validation_surface_index(*, generated_at: str | None = None) -> Dict[str, Any]:
    """Return the default public-safe validation surface index for SCLite v0.1.

    The index describes what a reviewer can validate locally. It does not claim
    live execution, authorization, or protocol adapter coverage.
    """
    surfaces = [
        {
            'surface_id': 'security_contract_proof_fixture',
            'path': 'examples/security-contract-proof',
            'kind': 'fixture_directory',
            'purpose': 'Validate the public-safe proof trace artifact chain.',
            'schemas': [
                'policy_decision.v0.1',
                'redacted_prepared_execution_spec.v0.1',
                'approved_execution_spec.v0.1',
                'execution_receipt.v0.1',
                'evidence_bundle.v0.1',
            ],
            'commands': ['sclite validate examples/security-contract-proof'],
            'public_safe': True,
        },
        {
            'surface_id': 'prepared_execution_spec_fixture',
            'path': 'examples/prepared-execution-spec/prepared_execution_spec.json',
            'kind': 'json_artifact',
            'purpose': 'Validate the draft prepared execution shape before approval.',
            'schemas': ['prepared_execution_spec.v0.1'],
            'commands': ['sclite validate-artifact --schema prepared_execution_spec.v0.1 examples/prepared-execution-spec/prepared_execution_spec.json'],
            'public_safe': True,
        },
        {
            'surface_id': 'scope_fidelity_fixture',
            'path': 'examples/scope-fidelity-report/scope_fidelity_report.json',
            'kind': 'json_artifact',
            'purpose': 'Validate static target-host binding review output.',
            'schemas': ['scope_fidelity_report.v0.1'],
            'commands': ['sclite validate-artifact --schema scope_fidelity_report.v0.1 examples/scope-fidelity-report/scope_fidelity_report.json'],
            'public_safe': True,
        },
        {
            'surface_id': 'lifecycle_review_fixture',
            'path': 'examples/lifecycle-review/review_record.json',
            'kind': 'json_artifact',
            'purpose': 'Validate a static lifecycle ReviewRecord aggregate with Scope Fidelity v0.2.',
            'schemas': ['review_record.v0.1', 'scope_fidelity_report.v0.2'],
            'commands': ['sclite review-lifecycle sclite/examples/contract-lifecycle-v0.2/artifact_chain_manifest.json --format json'],
            'public_safe': True,
        },
        {
            'surface_id': 'review_bundle_fixture',
            'path': 'examples/review-bundle',
            'kind': 'review_bundle_directory',
            'purpose': 'Validate and export a canonical SCLite v0.5 review bundle.',
            'schemas': ['review_record.v0.1', 'artifact_chain_manifest.v0.2'],
            'commands': ['sclite review examples/review-bundle --format json', 'sclite export-review-bundle examples/review-bundle --format markdown'],
            'public_safe': True,
        },
        {
            'surface_id': 'govengine_integration_fixture',
            'path': 'examples/govengine-integration',
            'kind': 'review_bundle_directory',
            'purpose': 'Validate the SCLite 0.5.x downstream integration fixture for GovEngine consumption.',
            'schemas': ['review_record.v0.1', 'artifact_chain_manifest.v0.2', 'execution_ticket.v0.3', 'trust_profile_ref.v0.1', 'carrier_profile_ref.v0.1'],
            'commands': [
                'sclite review examples/govengine-integration --format json --fail-on review',
                'sclite validate-trust-profile examples/govengine-integration/trust_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json',
                'sclite validate-carrier-profile examples/govengine-integration/carrier_profile_ref.json --subject examples/govengine-integration/04_execution_ticket.json',
            ],
            'public_safe': True,
        },
    ]
    return {
        'artifact_type': PUBLIC_VALIDATION_SURFACE_INDEX_ARTIFACT_TYPE,
        'schema_version': PUBLIC_VALIDATION_SURFACE_INDEX_SCHEMA_VERSION,
        'generated_at': generated_at or _utc_now(),
        'surfaces': surfaces,
        'summary': {
            'surface_count': len(surfaces),
            'public_safe_surface_count': sum(1 for item in surfaces if item.get('public_safe') is True),
        },
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
        entry: Dict[str, Any] = {
            'path': str(item.get('path') or ''),
            'artifact_type': str(item.get('artifact_type') or ''),
            'schema': str(item.get('schema') or ''),
            'public_safe': bool(item.get('public_safe', True)),
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
            'public_safe_file_count': sum(1 for item in normalized if item.get('public_safe') is True),
        },
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
    import json

    entries: list[Dict[str, Any]] = []
    for path in paths:
        value = json.loads(path.read_text(encoding='utf-8'))
        artifact_type = value.get('artifact_type') if isinstance(value, dict) else ''
        entries.append({
            'path': str(path),
            'artifact_type': str(artifact_type or ''),
            'schema': schema,
            'public_safe': True,
            'value': value,
        })
    return entries
