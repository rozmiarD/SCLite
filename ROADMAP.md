# SCLite Roadmap

Current source package: `sclite-core==2.0.1`.

Latest published public package: `sclite-core==2.0.0`.

Source status: unpublished non-prerelease 2.0.1 release source; publication pending.

SCLite 2.0 is the frozen truth, contract, evidence-integrity and verification
layer used by the current stack. This roadmap describes maintenance work only.
The detailed pre-2.0 version history is archived in
[`docs/archive/ROADMAP_VERSION_HISTORY.md`](docs/archive/ROADMAP_VERSION_HISTORY.md);
release history remains in [`CHANGELOG.md`](CHANGELOG.md).

## Ownership

```text
SCLite   canonical artifacts, hashing, lifecycle/evidence integrity, review and verification
GovEngine governance, admission, approval requirements, obligations and constraints
RExecOp  domain-neutral lifecycle, scheduling, connectors, retries and execution
Profiles domain vocabulary, intent catalogs, workflows and validation
```

SCLite does not execute operations, decide governance, own runtime lifecycle,
store raw evidence, resolve secrets, operate a replay database or define domain
semantics.

## 2.0 maintenance policy

The 2.0 public API, schemas, canonicalization rules, verifier profiles and
conformance vectors are frozen. Maintenance may:

- correct documentation and executable examples;
- strengthen tests, validators and release gates without changing accepted
  contracts;
- repair implementation bugs while preserving documented compatibility;
- update packaging or supply-chain tooling without widening runtime scope;
- improve language-neutral conformance evidence for existing behavior.

Maintenance must not:

- add runtime, scheduler, connector, policy or domain behavior;
- add a schema merely to mirror a GovEngine, RExecOp or profile-owned fact;
- silently change canonical bytes, digests, HMAC transcripts, profile meanings
  or fail-closed verification semantics;
- broaden the top-level API without a concrete consumer, compatibility analysis
  and an explicit release decision.

Any incompatible correction requires a new contract/profile identity or a new
major version. A request for a new SCLite contract is a stop condition until
ownership and necessity are demonstrated against live consumers.

## Active maintenance backlog

### Documentation truth

- Keep README, status, specification, security model, integration guidance and
  examples aligned with the shipped wheel.
- Execute documented CLI examples through the correct kernel or devtools
  entrypoint.
- Keep historical product lines out of active current-surface documentation.

### Anti-drift

- Validate active Markdown against the actual CLI command registry.
- Reject references to missing tests and current-release wording from retired
  lines.
- Keep the machine-readable consumer inventory aligned with the 2.0 line and
  controlled consumer imports.
- Keep source and packaged example documentation byte-identical.

### Compatibility and security

- Preserve the 2.0 consumer import contract for GovEngine, RExecOp and Tecrax.
- Run public-truth, strict-schema, security-regression, conformance, package and
  downstream import gates before a maintenance release.
- Keep release evidence bound to reviewed source and reproducible artifacts.

## Release posture

Documentation changes on `main` do not require a package release. A patch
release is justified only when the published package itself needs a meaningful
maintenance correction and the exact-pin release train has been evaluated.

Before any tag or upload:

1. verify version and dependency truth across controlled consumers;
2. run the full development and package gates;
3. compare clean wheel and sdist builds;
4. verify external review/release evidence;
5. obtain explicit release approval;
6. verify the published artifact through a clean PyPI install.

SCLite `2.0.1` is the feature-freeze-compatible maintenance source for the
corrections above. It is broader than metadata repair, remains unpublished, and
publication is pending an explicit release decision.
