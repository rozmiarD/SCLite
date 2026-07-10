# SCLite Security Profiles

This document freezes the public meaning of SCLite security profiles for the
1.0 release line.

| Profile | Owner | Meaning | Failure Mode | Status |
| --- | --- | --- | --- | --- |
| `integrity_only` | SCLite | SHA-256 artifact-chain consistency for canonical JSON artifacts | fails when descriptors, chain links, or root digest mismatch | core/current |
| `strict_lifecycle` | SCLite | `integrity_only` plus exact v0.2 lifecycle role sequence, role/schema identity, and semantic lifecycle bindings | fails on extra roles, duplicate roles, reorder, schema identity drift, or lifecycle digest mismatch | core/current |
| `guarded_domain_auth` | SCLite | `strict_lifecycle` plus `kernel_guard_hmac_v1` sidecar authenticity inside a shared-secret domain | fails on missing/mismatched guard fields, tags, metadata digest, root tag, or wrong key | secure/current |
| `guarded-strict` | SCLite | fail-closed secure bundle profile: artifact chain, strict lifecycle, Kernel Guard HMAC, and manifest metadata binding | fails closed when guard is missing or any layer fails | stable baseline |
| `legacy_read_only_guard` | SCLite | historical HMAC verification with an explicitly selected sub-32-byte key policy | never satisfies `guarded_domain_auth` or `guarded-strict`; entropy remains not checked | compatibility/read-only |
| `guarded_domain_auth_fresh` | GovEngine or host runtime | `guarded-strict` plus replay freshness/state | outside SCLite; host must reject replayed roots or payloads | host-owned |
| `public_signed_export` | future optional profile | public root signature or public anchor for third-party verification | not implemented | out of scope |

## Profile Rules

- SCLite owns verification of local artifacts, lifecycle shape, digest chains,
  and optional Kernel Guard HMAC sidecars.
- SCLite does not own replay freshness because replay requires state.
- SCLite does not own public identity or non-repudiation because HMAC requires
  a shared secret.
- `verify-secure-bundle` is the public CLI/API entry point for the
  `guarded-strict` profile.
- `guarded-strict` treats the manifest and Kernel Guard sidecar as
  root-contained bundle inputs after path and symlink resolution.
- `guarded-strict` also reports static ticket-use status for v0.3
  receipt-bounded evidence and fails on bounded-evidence violations when those
  artifacts are present.
- `guarded_domain_auth_fresh` belongs to GovEngine or another host layer that
  can keep replay state and make runtime admission decisions.

## Compatibility Rules

The following are compatibility-critical for the current `kernel_guard_hmac_v1`
profile:

- deterministic JSON canonicalization settings;
- `manifest_metadata_digest()` semantics;
- per-entry transcript fields;
- root transcript fields;
- HMAC-SHA256 tag calculation;
- constant-time tag comparison with `hmac.compare_digest`.
- Kernel Guard sidecar schema validation remains enforced independently from
  artifact schema validation.

An incompatible change must use a new profile name. Do not change
`kernel_guard_hmac_v1` semantics silently.

## Non-Claims

These profiles do not claim:

- PKI or public identity;
- non-repudiation;
- legal authorization;
- runtime execution;
- runtime enforcement;
- replay freshness inside SCLite;
- carrier delivery or adapter correctness;
- KMS, key-store, or revocation support.
