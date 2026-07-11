# Release security gate

SCLite release tags use a fail-closed GitHub workflow with commit-SHA-pinned
actions, PyPI Trusted Publishing, GitHub artifact provenance, wheel and sdist
installation smoke tests, dependency auditing, an SBOM and reproducible-wheel
comparison under a fixed `SOURCE_DATE_EPOCH`.

The supported Python matrix, adversarial regression gate, property tests and
the language-neutral conformance corpus must pass before a tag is created.
Unresolved High or Critical findings block release.

The tag workflow reruns the full source and package gates, including Ruff,
strict mypy and the language-neutral Node.js conformance vectors,
requires `v<project.version>`, and for stable releases compares the review's
source commit, release line and two artifact SHA-256 values with the exact wheel
and sdist built for publication. Build and release-test tooling is
exact-version pinned, and package smoke uses the same minimal build requirements.
Both wheel and normalized sdist bytes must reproduce under the fixed epoch.

An external reviewer must record the reviewed source commit, candidate artifact
digests, scope and unresolved findings for the 2.0 release candidate. CI cannot
self-assert this human review. The release owner attaches that record to the RC
sign-off before promoting a stable tag.

Approval applies only to the exact release line, source commit and artifacts in
the record. Promotion from `2.0.0rc1` to `2.0.0` creates a new commit and new
artifacts, so the reviewer must confirm the final stable diff and hashes. Stable
record validation requires explicit source-commit, release-line and exactly two
artifact arguments; shape-only inspection is not a stable release approval.

Stable release uses two commits to avoid a self-referential record:

1. source commit `A` contains the final stable code/version and is reviewed;
2. record commit `B` has exactly one parent (`A`) and changes only
   `security/EXTERNAL_REVIEW.json`;
3. the stable tag points to `B`;
4. the workflow proves the parent/diff relationship, preserves the record,
   checks out `A`, runs Python 3.11-3.13 gates, and builds candidate artifacts;
5. the workflow checks out `B`, rebuilds, requires identical artifact names and
   bytes to the build from `A`, and publishes/attests the build from `B`;
6. source and artifact hashes are checked before publication. Standard GitHub
   provenance therefore identifies the commit actually used for the published
   build (`B`), while the equality gate binds those bytes to reviewed source
   commit `A`.

The publish job exports `SOURCE_DATE_EPOCH=1704067200` for every package build.
Regular CI also creates a real record-only child commit, waits across a clock
tick, builds both commits and runs the same byte-comparison gate.

The completion record is release-owner-attested metadata. CI verifies strict
record shape and source/artifact binding, but does not authenticate reviewer
identity, reviewer consent, or report authorship. `report_sha256` records the
release owner's claimed digest of the retained report. CI validates its format
but does not retrieve or hash the report. Review date/verdict, all severity
counts and accepted finding IDs preserve the handoff to that separately shared
report.

For `approved_with_low_or_medium_findings`, accepted IDs use `M-...` and
`L-...` prefixes and their per-severity counts must match the unresolved Medium
and Low counters. Review dates must be real ISO calendar dates.

Security-sensitive descriptor traversal and release tooling are supported and
tested on Linux/Unix. Windows secure-bundle and release-tooling behavior is not
claimed unless separately implemented and tested.
