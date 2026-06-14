from __future__ import annotations

from pathlib import Path

import sclite


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_PUBLIC_EXPORTS = (
    '__version__',
    'REVIEW_BUNDLE_MANIFEST_FILE',
    'REVIEW_BUNDLE_MARKDOWN_FILE',
    'REVIEW_BUNDLE_RECEIPT_FILE',
    'REVIEW_BUNDLE_REQUIRED_FILES',
    'ReviewBundleError',
    'export_review_bundle_markdown',
    'materialize_review_bundle',
    'review_bundle',
    'review_bundle_summary',
    'validate_review_bundle_shape',
    'CHAIN_CANONICALIZATION_VERSION',
    'CHAIN_HASH_ALGORITHM',
    'ChainVerificationError',
    'artifact_descriptor',
    'build_artifact_chain_manifest',
    'verify_artifact_chain_manifest',
    'verify_lifecycle_manifest',
    'KERNEL_GUARD_PROFILE',
    'KernelGuardError',
    'build_kernel_guard_manifest',
    'manifest_metadata_digest',
    'verify_kernel_guard_manifest',
    'SECURE_BUNDLE_POSTURE',
    'SECURE_BUNDLE_PROFILE',
    'SecureBundleError',
    'resolve_guard_path',
    'resolve_manifest_path',
    'verify_secure_bundle',
    'VERIFICATION_RESULT_SCHEMA_REF',
    'build_guarded_strict_verification_result',
    'REVIEW_RECORD_SCHEMA',
    'REVIEW_RECORD_SCHEMA_REF',
    'ReviewRecordError',
    'build_review_record_from_manifest',
    'review_record_markdown',
    'LIFECYCLE_SCOPE_FIDELITY_SCHEMA_REF',
    'LIFECYCLE_SCOPE_FIDELITY_SCHEMA_VERSION',
    'SCOPE_FIDELITY_ARTIFACT_TYPE',
    'SCOPE_FIDELITY_SCHEMA_REF',
    'SCOPE_FIDELITY_SCHEMA_VERSION',
    'build_lifecycle_scope_fidelity_report',
    'build_scope_fidelity_report',
    'build_scope_fidelity_report_from_approved_spec',
    'summarize_scope_fidelity',
    'validate_lifecycle_scope_fidelity_report',
    'validate_scope_fidelity_report',
    'SCOPED_TICKET_SCHEMA_REF',
    'TICKET_PROFILES',
    'TicketSemanticError',
    'TicketUseVerificationError',
    'explain_ticket',
    'normalized_args_digest',
    'ticket_summary',
    'validate_ticket_schema',
    'validate_ticket_semantics',
    'verify_ticket_use',
)


def test_top_level_public_api_exports_are_frozen() -> None:
    assert sclite.__all__ == EXPECTED_PUBLIC_EXPORTS
    for name in EXPECTED_PUBLIC_EXPORTS:
        assert hasattr(sclite, name), name


def test_public_api_doc_lists_all_frozen_exports() -> None:
    text = (ROOT / 'docs' / 'PUBLIC_API.md').read_text(encoding='utf-8')
    for name in EXPECTED_PUBLIC_EXPORTS:
        assert f'`{name}`' in text
