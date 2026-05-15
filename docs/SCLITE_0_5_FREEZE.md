# SCLite 0.5 Freeze Notes

These notes define what is stable for GovEngine consumption in the `sclite-core>=0.5.1,<0.6` line.

## Stable for GovEngine consumption

GovEngine may rely on:

- v0.2 lifecycle artifact order:
  `intent_contract -> policy_decision -> execution_contract -> execution_ticket -> execution_receipt -> evidence_contract`;
- artifact descriptor shape returned by `sclite.integrity.artifact_descriptor`;
- artifact-chain manifest verification semantics in `verify_artifact_chain_manifest`;
- canonical review-bundle filenames:
  - `01_intent_contract.json`
  - `02_policy_decision.json`
  - `03_execution_contract.json`
  - `04_execution_ticket.json`
  - `05_execution_receipt.json`
  - `06_evidence_contract.json`
  - `artifact_chain_manifest.json`
  - `REVIEW.md`
  - `verification_receipt.json`
- `execution_ticket.v0.3` scoped-ticket semantics;
- `verify_ticket_use()` result shape and conservative failure behavior;
- `review_record.v0.1` result shape with `verdict`, `summary`, `checks`, and `non_claims`;
- `trust_profile_ref.v0.1` digest-binding semantics;
- `carrier_profile_ref.v0.1` digest-binding semantics;
- CLI exit-code semantics documented in [`CLI_EXIT_CODES.md`](CLI_EXIT_CODES.md).

## Not guaranteed stable

The following are not part of the GovEngine freeze contract:

- helper functions not listed in [`GOVENGINE_INTEGRATION_CONTRACT.md`](GOVENGINE_INTEGRATION_CONTRACT.md);
- Markdown formatting of `REVIEW.md` or exported review text;
- example prose and fixture wording;
- legacy v0.1 compatibility internals beyond public fixture validation;
- private/non-public helper functions;
- exact exception classes/messages beyond non-zero failure behavior for CLI gates.

## Boundary freeze

SCLite 0.5 remains limited to:

```text
define / validate / hash / bind / redact / review
```

SCLite does not own:

- live execution;
- scanner/tool wrappers;
- approval authority;
- policy decisions;
- signer identity or PKI trust;
- revocation;
- carrier delivery;
- GovEngine orchestration;
- Ravenclaw runtime behavior.

GovEngine should consume SCLite as a proof/review substrate, not as an execution authority.
