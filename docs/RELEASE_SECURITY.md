# Release security gate

SCLite release tags use a fail-closed GitHub workflow with commit-SHA-pinned
actions, PyPI Trusted Publishing, GitHub artifact provenance, wheel and sdist
installation smoke tests, dependency auditing, an SBOM and reproducible-wheel
comparison under a fixed `SOURCE_DATE_EPOCH`.

The supported Python matrix, adversarial regression gate, property tests and
the language-neutral conformance corpus must pass before a tag is created.
Unresolved High or Critical findings block release.

The tag workflow reruns the full source and package gates for the tagged SHA,
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
