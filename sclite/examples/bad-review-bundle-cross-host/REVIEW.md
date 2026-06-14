# SCLite Review Record

verdict: `fail`
review_profile: `sclite-review-bundle-v0.1`
source_manifest: `artifact_chain_manifest.json`

## Checks
- `pass` — schema_validation: all manifest artifacts validated against declared schemas
- `pass` — chain_integrity: 713966993dabb224cc2d4501129f650331cc33d8070dcba144e275f62b2d6b7f
- `pass` — lifecycle_binding: semantic checks present
- `fail` — scope_fidelity: mismatched lifecycle target hosts: evil.example.net,example.com
- `pass` — ticket_use_profile: ticket-use verification passed

## Non-claims
- does_not_execute_tools
- does_not_prove_legal_authorization
- does_not_prove_signer_identity
- does_not_prove_carrier_delivery
- does_not_replace_runtime_policy_decision
