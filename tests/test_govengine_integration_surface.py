from __future__ import annotations


def test_govengine_stable_import_surface() -> None:
    from sclite.bundles import review_bundle, validate_review_bundle_shape
    from sclite.integrity import artifact_descriptor, verify_artifact_chain_manifest
    from sclite.profiles import validate_carrier_profile_ref, validate_trust_profile_ref
    from sclite.review import build_review_record_from_manifest
    from sclite.scope_fidelity import build_lifecycle_scope_fidelity_report
    from sclite.tickets import validate_ticket_semantics, verify_ticket_use

    assert callable(artifact_descriptor)
    assert callable(verify_artifact_chain_manifest)
    assert callable(validate_ticket_semantics)
    assert callable(verify_ticket_use)
    assert callable(build_review_record_from_manifest)
    assert callable(review_bundle)
    assert callable(validate_review_bundle_shape)
    assert callable(validate_trust_profile_ref)
    assert callable(validate_carrier_profile_ref)
    assert callable(build_lifecycle_scope_fidelity_report)
