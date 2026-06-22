# SCLite Public API

SCLite `1.0` keeps a deliberately small top-level Python API through
`import sclite`. These names are the stable convenience surface. Deeper module
imports remain available for advanced users, but removal or rename of the
top-level exports below is a compatibility change.

SCLite does not expose runtime execution, replay storage, PKI, KMS, policy
authority, or carrier adapters through this API.

## Version

- `__version__`

## Review Bundles

- `REVIEW_BUNDLE_MANIFEST_FILE`
- `REVIEW_BUNDLE_MARKDOWN_FILE`
- `REVIEW_BUNDLE_RECEIPT_FILE`
- `REVIEW_BUNDLE_REQUIRED_FILES`
- `ReviewBundleError`
- `export_review_bundle_markdown`
- `materialize_review_bundle`
- `review_bundle`
- `review_bundle_summary`
- `validate_review_bundle_shape`

## Artifact Chain

- `CHAIN_CANONICALIZATION_VERSION`
- `CHAIN_HASH_ALGORITHM`
- `ChainVerificationError`
- `artifact_descriptor`
- `build_artifact_chain_manifest`
- `verify_artifact_chain_manifest`
- `verify_lifecycle_manifest`

## Deterministic Reaction Artifacts

- `OBSERVATION_SCHEMA_REF`
- `FINDING_SCHEMA_REF`
- `REACTION_PLAN_SCHEMA_REF`
- `ESCALATION_PROPOSAL_SCHEMA_REF`
- `build_observation_envelope`
- `build_finding`
- `build_reaction_plan`
- `build_reaction_chain_manifest`
- `reaction_idempotency_key`
- `validate_escalation_proposal`
- `verify_reaction_chain_manifest`

These functions define and verify the canonical evidence boundary. They do not
interpret profile rules, authorize a reaction, or execute an operation.

## Kernel Guard And Secure Bundles

- `KERNEL_GUARD_PROFILE`
- `KernelGuardError`
- `build_kernel_guard_manifest`
- `manifest_metadata_digest`
- `verify_kernel_guard_manifest`
- `SECURE_BUNDLE_POSTURE`
- `SECURE_BUNDLE_PROFILE`
- `SecureBundleError`
- `resolve_guard_path`
- `resolve_manifest_path`
- `verify_secure_bundle`

## Verification Result

- `VERIFICATION_RESULT_SCHEMA_REF`
- `build_guarded_strict_verification_result`

## Review Records

- `REVIEW_RECORD_SCHEMA`
- `REVIEW_RECORD_SCHEMA_REF`
- `ReviewRecordError`
- `build_review_record_from_manifest`
- `review_record_markdown`

## Scope Fidelity

- `LIFECYCLE_SCOPE_FIDELITY_SCHEMA_REF`
- `LIFECYCLE_SCOPE_FIDELITY_SCHEMA_VERSION`
- `SCOPE_FIDELITY_ARTIFACT_TYPE`
- `SCOPE_FIDELITY_SCHEMA_REF`
- `SCOPE_FIDELITY_SCHEMA_VERSION`
- `build_lifecycle_scope_fidelity_report`
- `build_scope_fidelity_report`
- `build_scope_fidelity_report_from_approved_spec`
- `summarize_scope_fidelity`
- `validate_lifecycle_scope_fidelity_report`
- `validate_scope_fidelity_report`

## Tickets

- `SCOPED_TICKET_SCHEMA_REF`
- `TICKET_PROFILES`
- `TicketSemanticError`
- `TicketUseVerificationError`
- `explain_ticket`
- `normalized_args_digest`
- `ticket_summary`
- `validate_ticket_schema`
- `validate_ticket_semantics`
- `verify_ticket_use`

## Compatibility Rule

Patch releases may add new names, but should not remove or rename these exports
without a new major compatibility decision. Changes to Kernel Guard transcript
or canonical JSON behavior require a new profile name rather than a silent API
change.
