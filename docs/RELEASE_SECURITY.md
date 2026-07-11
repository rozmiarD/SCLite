# Release security gate

SCLite release tags use a fail-closed GitHub workflow with commit-SHA-pinned
actions, PyPI Trusted Publishing, GitHub artifact provenance, wheel and sdist
installation smoke tests, dependency auditing, an SBOM and reproducible-wheel
comparison under a fixed `SOURCE_DATE_EPOCH`.

The supported Python matrix, adversarial regression gate, property tests and
the language-neutral conformance corpus must pass before a tag is created.
Unresolved High or Critical findings block release.

An external reviewer must record the reviewed source commit, candidate artifact
digests, scope and unresolved findings for the 2.0 release candidate. CI cannot
self-assert this human review. The release owner attaches that record to the RC
sign-off before promoting a stable tag.
