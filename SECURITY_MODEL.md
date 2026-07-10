# SCLite Security Model

SCLite is a local artifact validation and review substrate. It defines,
validates, hashes, binds, redacts, verifies, and reviews public-safe contract
artifacts.

SCLite is not a runtime, policy authority, PKI, key store, replay store,
transparency log, carrier adapter, scanner, or executor.

## Security Layers

SCLite deliberately separates local integrity from authenticity and runtime
freshness.

| Layer | SCLite Surface | Guarantees | Non-Claims |
| --- | --- | --- | --- |
| `integrity_only` | `validate-chain`, artifact descriptors, `root_chain_digest` | local SHA-256 consistency for canonical JSON artifacts and ordered manifest links | no origin authenticity, no signer identity, no replay protection |
| `strict_lifecycle` | `verify-lifecycle`, `require_lifecycle=True` | exact v0.2 lifecycle role sequence with no extra roles, duplicates, or reorder; semantic digest bindings across lifecycle artifacts | no runtime enforcement, no policy authorization, no legal authorization |
| `guarded_domain_auth` | `kernel_guard_hmac_v1`, `verify-guarded-chain` | HMAC-SHA256 domain authenticity for a manifest and entries when the verifier knows the same domain secret | no public verification, no PKI, no non-repudiation, no replay freshness |
| `guarded-strict` | `verify-secure-bundle` | fail-closed artifact-chain verification, strict lifecycle, Kernel Guard HMAC, and manifest metadata binding | no replay freshness, no public identity, no runtime execution proof |
| `guarded_domain_auth_fresh` | GovEngine/host replay store | guarded-strict plus host-owned freshness/state decision | outside SCLite core |

Verifier JSON surfaces expose layer-specific status fields so callers cannot
mistake one layer for another:

- `validate-chain` returns `chain_status: passed` and
  `verification_posture: integrity_only` with
  `lifecycle_status: not_checked` unless strict lifecycle verification is
  explicitly requested.
- `verify-lifecycle` returns `chain_status: passed` and
  `verification_posture: strict_lifecycle` with `lifecycle_status: passed`
  after v0.2 lifecycle role, schema identity, and digest semantics pass.
- `verify-guarded-chain` adds `guard_status: passed` while keeping
  `replay_status: not_checked`.
- `verify-secure-bundle` combines `chain_status`, `lifecycle_status`,
  `guard_status`, `ticket_use_status`, and `replay_status` with the stable
  `verification_result.v1` non-claim fields.

`VerificationResult` is a frozen convenience type, not a capability or proof
token. Python code can instantiate it, and schema-valid JSON can be forged.
Acceptance therefore requires re-verifying the referenced bundle or receiving
the result through a separately authenticated trusted channel. The additive
v1.1 serializer records bundle digest, selected policy, verifier version and
performed checks so a host can bind acceptance to explicit provenance.

## Canonicalization Freeze

SCLite artifact and Kernel Guard verification rely on deterministic JSON:

- `json.dumps(..., sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)`
- UTF-8 bytes
- SHA-256 for artifact descriptors and manifest metadata digests
- HMAC-SHA256 for `kernel_guard_hmac_v1`

For the `kernel_guard_hmac_v1` profile, the transcript layout is
compatibility-critical. SCLite must not silently change:

- the canonical JSON settings used for transcript bytes;
- per-entry transcript fields;
- root transcript fields;
- `manifest_metadata_digest()` exclusions;
- tag comparison semantics.

Any incompatible change requires a new profile name, for example
`kernel_guard_hmac_v2`.

## Schema Source Boundary

Artifact `schema_ref` values are treated as contract identifiers, not as
authority to load arbitrary local files from an untrusted bundle. By default
SCLite resolves schema references to packaged SCLite schemas only, accepting
canonical schema ids such as `execution_ticket.v0.3` and packaged refs such as
`schemas/execution_ticket.v0.3.schema.json`. Path-like aliases that merely end
with a packaged schema filename are not treated as packaged refs.

External schema files are available only through explicit caller opt-in in the
Python API. CLI `validate-artifact --schema PATH` remains an operator-supplied
local validation action, but artifact-chain and review-bundle verification do
not let bundle-provided `schema_ref` values override packaged schemas.
When an external schema is explicitly allowed with a `root`, SCLite resolves
exactly that root-contained path and rejects `..` or symlink escapes. There is
no fallback to repository-local schema files for untrusted artifact refs.

## Kernel Guard HMAC v1

`kernel_guard_hmac_v1` is a sidecar profile. It does not mutate artifact
bodies and does not change artifact descriptor digest rules.

Per-entry transcripts bind:

- profile, chain id, sequence, and entry count;
- role, path, and `required`;
- descriptor digest, artifact type, schema ref, schema version,
  canonicalization, and hash algorithm;
- previous HMAC tag, nonce, and key id.

The root transcript binds:

- profile and chain id;
- entry count;
- first and last entry tag;
- current `root_chain_digest`;
- manifest metadata digest;
- key id.

This prevents tampering or reordering by an attacker who cannot compute HMACs
for the domain secret. It does not prove public identity.

Kernel Guard sidecar schema validation is separate from artifact schema
validation. CLI `--no-schema` skips artifact schema checks for hash/link
verification only; it does not silently disable the guard sidecar shape check.

For `verify-secure-bundle`, the default sidecar path is
`kernel_guard_manifest.json` next to the resolved artifact-chain manifest. An
explicit guard path is resolved as the caller supplied it, but the
`guarded-strict` secure-bundle profile requires both the manifest and resolved
guard sidecar to remain under the verification root after symlink resolution.
The lower-level `verify-guarded-chain` command remains an operator-supplied
local guard check and does not turn an external sidecar into a bundle member.

## Replay Boundary

SCLite reports replay as `not_checked`.

Replay freshness requires state. State does not belong in SCLite's pure local
verifier. GovEngine or another host runtime must own replay storage and
freshness decisions for runtime-consumable bundles.

Production replay stores should provide atomic check-and-set behavior for the
freshness key, such as a database transaction, unique index, Redis `SETNX`, or
equivalent host-owned mechanism. A local JSON replay file is acceptable for
demo and development use, but it is not a concurrent production freshness
primitive by itself.

Host freshness handoff data should be enough for the host to claim one runtime
use atomically without asking SCLite to keep state. Typical inputs are
`root_chain_digest`, `guard_root_tag`, `chain_id`, `key_id`, ticket/run id, the
host's observed time, and the host admission context. TTL, concurrency,
cleanup, replay persistence, and collision policy are host-owned.

A minimal handoff record should look like this shape:

```json
{
  "root_chain_digest": "<artifact-chain root digest>",
  "guard_root_tag": "<kernel_guard_hmac_v1 root tag when present>",
  "chain_id": "<manifest chain_id>",
  "key_id": "<guard key_id when guarded>",
  "ticket_id": "<execution ticket id>",
  "run_id": "<host-owned run/admission id>",
  "observed_at": "<host observation timestamp>",
  "host_admission_context": "<host-owned policy/admission reference>",
  "verifier_profile": "guarded-strict"
}
```

SCLite may define, emit, or document this handoff shape, but the atomic
freshness decision and storage remain GovEngine/host responsibilities.

## Key IDs And Rotation

`key_id` identifies the domain/season of the HMAC key used to create a guard.

SCLite verifies guard material with the key supplied by the caller. It does not:

- generate long-lived production secrets;
- store keys;
- rotate keys;
- revoke keys;
- prove which operator or service controlled a key.

Production Guard creation and verification accept only `str|bytes` keys with
at least 32 bytes after UTF-8 encoding. This is a configuration floor, not an
entropy measurement: even a 32-byte repeated value is accepted and reported as
`key_entropy_status="not_checked"`. Common placeholder markers produce a
warning but do not change that non-claim. The explicit legacy read-only policy
may inspect historical short-key guards and always returns the weaker
`legacy_read_only_guard` posture; it cannot satisfy `guarded-strict`.

Old guarded bundles can be verified only while the caller still has the
corresponding key for their `key_id`. Key rotation, compromise response, and
key retention policy are host responsibilities.

If a Kernel Guard secret is compromised, an attacker may create valid-looking
guards for that key domain. SCLite cannot distinguish those from legitimate
guards without an external trust, revocation, or publication mechanism.

## Public Identity And Signatures

HMAC gives authenticity only to parties that already share the secret. It is
not public verification and it is not non-repudiation.

Future public export may add a separate profile such as an Ed25519 root
signature. That is intentionally out of scope for the current SCLite 1.0
release line.

## Runtime And Policy Boundary

SCLite artifacts can describe intent, policy decisions, execution contracts,
tickets, receipts, and evidence. They do not execute those artifacts.

SCLite does not decide whether an action is authorized, safe to run, legally
permitted, or actually enforced by a runtime. A host such as GovEngine or
Ravenclaw must own runtime admission, replay freshness, approval UX, execution
control, raw evidence storage, and operational policy.

## Threat Classes Covered

In `guarded-strict`, SCLite is intended to detect:

- artifact body tampering;
- descriptor or chain digest drift;
- extra lifecycle roles;
- duplicate lifecycle roles;
- lifecycle role reorder;
- manifest metadata spoofing;
- root-chain substitution;
- entry insertion with an old guard;
- previous-tag, nonce, key-id, or tag tampering;
- full-chain forgery by an attacker without the HMAC key.

## Threat Classes Not Covered

SCLite does not protect against:

- replay of an old valid guarded bundle without host replay state;
- compromise of the HMAC secret;
- malicious or compromised guard producer;
- malicious host runtime;
- public third-party verification without sharing a secret;
- legal authorization failures;
- runtime policy bypass outside the artifact verifier;
- raw evidence or log tampering outside SCLite-managed artifacts.
