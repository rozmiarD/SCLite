# SCLite Public API

SCLite `2.0` keeps a deliberately small top-level Python API through
`import sclite`. These names are the stable convenience surface. Deeper module
imports remain available for advanced users, but removal or rename of the
top-level exports below is a compatibility change.

SCLite does not expose runtime execution, replay storage, PKI, KMS, policy
authority, or carrier adapters through this API.

The wheel ships `sclite/contracts/consumer_imports.v1.json`, a machine-readable
inventory for the controlled GovEngine, RExecOp and Tecrax consumers. Every
root export has an explicit `stable`, `bridge`, `testing` or `internal`
classification, owner and disposition. Consumer CI scans production Python AST
imports against that allowlist; a new deep import fails until the contract is
reviewed. This inventory does not claim knowledge of private or external PyPI
consumers.

Installed `sclite` and `scl` entrypoints accept kernel validation,
verification, ticket and review workflows. Local inspection, snapshot,
scope-report and redaction-helper commands use `sclite-devtools`; passing one
of those commands to the kernel entrypoint fails with an instruction to use
the devtools entrypoint. The removed `python -m sclite.cli` compatibility
dispatcher is not available in 2.0; module invocation uses
`sclite.kernel_cli` or `sclite.devtools` explicitly.

## Version

- `__version__`

## Typed front door

- `ArtifactDescriptor`
- `VerificationPolicy`
- `VerificationResult`
- `VerifiedArtifact`
- `VerifiedBundle`
- `artifact_descriptor`
- `verify_artifact`
- `verify_bundle`
- `verify_ticket_use`
- `materialize_review_bundle`

`verify_bundle()` requires an explicit `INTEGRITY`, `STRICT_LIFECYCLE`,
`GUARDED_LIFECYCLE` or `PUBLIC_REVIEW` policy; it never infers posture from the
input. Retained wrappers delegate to the same verification paths in 2.0.
Typed results are immutable self-described outcomes,
not authentication tokens or runtime capabilities.

## Explicit schema extensions

- `ImmutableSchemaResolver`
- `SchemaInventoryEntry`
- `SchemaResolutionError`
- `SchemaResolver`

Hosts may pass an immutable, namespaced contract set to `verify_artifact()`.
Resolution uses canonical in-memory JSON bytes and a stable SHA-256 inventory;
it performs no plugin discovery, imports, network access or global mutation.
Identifiers use `namespace/name@vN`. Conflicting definitions of the same
identifier are rejected before verification.

Reaction, trigger, watchdog and automation modules, schemas and root exports
are absent from SCLite 2.0. Their owner implementation and historical artifact
resolver live in RExecOp.

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

## Kernel Guard And Secure Bundles

- `KERNEL_GUARD_PROFILE`
- `KERNEL_GUARD_MINIMUM_KEY_BYTES`
- `KernelGuardKeyPolicy`
- `KernelGuardError`
- `build_kernel_guard_manifest`
- `manifest_metadata_digest`
- `verify_kernel_guard_manifest`

Kernel Guard builders and verifiers default to the production key policy:
`str|bytes`, at least 32 bytes after UTF-8 encoding. Verification results expose
the byte length, placeholder warnings and `key_entropy_status="not_checked"`.
The explicit `key_policy="legacy_read_only"` verifier mode may authenticate
historical short-key sidecars, but reports `legacy_read_only_guard` rather than
production `guarded_domain_auth`. Secure-bundle verification never uses the
legacy policy. SCLite does not estimate entropy or own key custody/rotation.
Calling the low-level verifier with `validate_chain=False` reports
`guard_hmac_only`; chain and lifecycle remain `not_checked`, and this posture
cannot satisfy guarded lifecycle verification.
- `SECURE_BUNDLE_POSTURE`
- `SECURE_BUNDLE_PROFILE`
- `SecureBundleError`
- `resolve_guard_path`
- `resolve_manifest_path`
- `verify_secure_bundle`
- `verify_secure_bundle_result`

## Verification Result

- `VERIFICATION_RESULT_SCHEMA_REF`
- `VERIFICATION_RESULT_SCHEMA_REF_V1_1`
- `VerificationResult`
- `serialize_verification_result`
- `SCLiteError`
- `SCLiteValidationError`
- `SCLiteSchemaValidationError`

`verify_secure_bundle_result()` returns a frozen `VerificationResult` only after
the guarded-strict verifier completes. `serialize_verification_result()` emits
`verification_result.v1.1` with bundle digest, policy, verifier version and
performed checks. The object and JSON remain forgeable representations, not
proof tokens; hosts must re-verify source bytes or use an authenticated trusted
channel.

`JsonSchemaValidationError` remains the compatibility name through 2.0. It now
inherits from `SCLiteSchemaValidationError` / `SCLiteValidationError`, carries
stable code `schema_validation_failed`, and no longer inherits from
`AssertionError`. Other public validation exceptions retain `ValueError`
compatibility through the same base hierarchy and expose stable `.code` values.

## Testing helpers

- `sclite.testing.build_guarded_strict_verification_result_fixture`

This helper intentionally creates forgeable v1 fixture JSON and performs no
verification. It is available only from the testing namespace.

## Disclosure status

- `DISCLOSURE_STATUS_ORDER`
- `DisclosureStatus`
- `DisclosureStatusError`
- `build_disclosure_status`
- `relative_public_path`
- `validate_disclosure_transition`

The monotonic disclosure model is `unknown → operator_asserted →
checks_performed → externally_verified`. SCLite 2.0 has no derived
`public_safe` boolean; publication authorization remains a separate host
decision.

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
