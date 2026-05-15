# Trust Profiles

SCLite trust profiles describe how an artifact may refer to an external trust or signature record without making SCLite a PKI, key store, certificate authority, or trust authority.

## Boundary

SCLite validates:

- the `TrustProfileRef` JSON shape;
- the named profile value;
- the descriptor link to the subject artifact;
- the digest binding between the sidecar reference and the subject artifact.

SCLite does **not** validate:

- signer identity;
- revocation;
- certificate chains;
- Sigstore/DSSE bundle authenticity;
- organizational authorization;
- whether execution may proceed.

External runtimes and verifiers decide trust. GovEngine may consume the profile reference as one input to a `TrustDecision`, but SCLite only verifies the public-safe binding.

## Profiles

Initial profile names:

- `none`
- `digest_only`
- `local_ed25519_ref`
- `dsse_envelope_ref`
- `sigstore_bundle_ref`
- `external_verifier`

These are reference shapes, not bundled verifier implementations.

## Sidecar shape

A trust profile reference is a sidecar artifact with this core structure:

```json
{
  "artifact_type": "trust_profile_ref",
  "schema_version": "v0.1",
  "schema_ref": "schemas/trust_profile_ref.v0.1.schema.json",
  "trust_profile": "digest_only",
  "links": {
    "subject": {
      "role": "subject",
      "descriptor": { "digest": "..." }
    }
  },
  "integrity": {
    "subject_artifact_digest": "...",
    "binding_mode": "subject_descriptor_digest"
  },
  "verification_boundary": {
    "sclite_validates_digest_binding_only": true,
    "external_verifier_decides_trust": true
  }
}
```

## CLI

```bash
sclite validate-trust-profile \
  sclite/examples/trust-carrier-profiles/trust_profile_ref.json \
  --subject sclite/examples/scoped-ticket-v0.3/execution_ticket.json
```

The command passes when the sidecar profile reference is well-shaped and digest-bound to the subject artifact. It does not prove trust.
