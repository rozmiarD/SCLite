# SCLite Public API

SCLite `1.x` keeps a deliberately small top-level Python API through
`import sclite`. These names are the stable convenience surface. Deeper module
imports remain available for advanced users, but removal or rename of the
top-level exports below is a compatibility change.

SCLite does not expose runtime execution, replay storage, PKI, KMS, policy
authority, or carrier adapters through this API.

## Version

- `__version__`

## Verification Policy

- `VerificationLimits`

`VerificationLimits` defines finite defaults for per-file and aggregate JSON
bytes, nesting depth, parsed nodes, and manifest entries. Verification APIs use
the default policy when the caller does not provide one; a host may pass an
explicit policy with higher or lower limits. The strict loader always rejects
duplicate object keys and non-standard `NaN`/`Infinity` numbers.

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

`review_bundle()` and `validate_review_bundle_shape()` accept
`mode="local_review"` for diagnostic review or `mode="public_export"` for a
closed-world inventory check. `materialize_review_bundle()` defaults to
`public_export`, writes into a same-parent staged directory, verifies and
fsyncs it, and publishes by rename. It never replaces an existing directory
unless the caller explicitly passes `overwrite=True`.

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

## Trigger Decision Artifacts

- `TRIGGER_DECISION_SCHEMA`
- `TRIGGER_DECISION_SCHEMA_REF`
- `build_trigger_decision`
- `trigger_decision_descriptor`
- `trigger_decision_digest`
- `validate_trigger_decision`

These functions define the bounded truth-layer projection for trigger/event
decisions. They record event, rule, GovEngine admission and optional child
operation references. They do not match trigger rules, authorize planning,
schedule work, or execute an operation.

## Watchdog Decision Artifacts

- `WATCHDOG_DECISION_SCHEMA`
- `WATCHDOG_DECISION_SCHEMA_REF`
- `build_watchdog_decision`
- `watchdog_decision_descriptor`
- `watchdog_decision_digest`
- `validate_watchdog_decision`

These functions define the bounded truth-layer projection for runner watchdog
decisions. They record RExecOp runtime-supervisor observations, GovEngine
admission, affected operation/event/inbox references, and optional bounded
manual-recovery context for GovEngine-admitted recovery or break-glass records.
They do not supervise workers, run retries, authorize recovery, monitor
infrastructure health, or interpret profile semantics.

## Automation Chain Artifacts

- `AUTOMATION_CHAIN_ARTIFACT_TYPE`
- `AUTOMATION_CHAIN_NON_CLAIMS`
- `AUTOMATION_CHAIN_SCHEMA`
- `AUTOMATION_CHAIN_SCHEMA_REF`
- `automation_chain_digest`
- `automation_edge`
- `automation_node`
- `build_automation_chain`
- `validate_automation_chain`
- `verify_automation_chain`

These functions define and verify the bounded multi-step automation-chain
contract. The contract records nodes, edges, GovEngine admission refs,
idempotency keys, recovery policy, depth/reaction budgets and LLM non-authority
without executing operations, interpreting profile rules, or authorizing child
operations.

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

Minor releases may add new names, but should not remove or rename these exports
without a new major compatibility decision. Changes to Kernel Guard transcript
or canonical JSON behavior require a new profile name rather than a silent API
change.
