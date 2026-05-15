# Carrier Profiles

SCLite carrier profiles describe how an artifact may be packaged or referenced for transport without making SCLite a transport adapter, protocol implementation, or delivery authority.

## Boundary

SCLite validates:

- the `CarrierProfileRef` JSON shape;
- the named carrier profile value;
- the descriptor link to the subject artifact;
- the digest binding between the sidecar reference and the subject artifact.

SCLite does **not** validate:

- remote delivery;
- protocol correctness;
- message authenticity;
- queue state;
- runtime execution;
- OpenClaw, MCP, A2A, GitHub, or CI adapter behavior.

External carriers deliver payloads. GovEngine/domain runtimes may use carrier references as metadata, but SCLite only verifies public-safe binding.

## Profiles

Initial profile names:

- `local_file_bundle`
- `ci_artifact_bundle`
- `github_artifact`
- `govengine_bundle`
- `ravenclaw_review_bundle`
- `tecrax_review_bundle`
- `openclaw_carrier_payload`
- `mcp_message_ref`
- `a2a_message_ref`

These names reserve stable vocabulary. They do not imply adapter readiness.

## Sidecar shape

A carrier profile reference is a sidecar artifact with this core structure:

```json
{
  "artifact_type": "carrier_profile_ref",
  "schema_version": "v0.1",
  "schema_ref": "schemas/carrier_profile_ref.v0.1.schema.json",
  "carrier_profile": "local_file_bundle",
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
  "transport_boundary": {
    "sclite_validates_digest_binding_only": true,
    "external_carrier_delivers_payload": true
  }
}
```

## CLI

```bash
sclite validate-carrier-profile \
  sclite/examples/trust-carrier-profiles/carrier_profile_ref.json \
  --subject sclite/examples/scoped-ticket-v0.3/execution_ticket.json
```

The command passes when the sidecar carrier reference is well-shaped and digest-bound to the subject artifact. It does not prove delivery.
