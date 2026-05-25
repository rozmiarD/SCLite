# Security Policy

SCLite defines, validates, redacts, hashes, binds, and verifies public-safe Security Contract Layer artifacts.

It is not an executor, scanner, authorization authority, sandbox, or vulnerability proof system.

## Supported versions

The source tree currently prepares the unpublished `sclite-core==0.8.0b0`
beta candidate. The latest published package remains `sclite-core==0.8.0a0`.
Security fixes should target `main` until stable release branches exist.

## Reporting security issues

Please avoid posting credentials, private targets, raw logs, exploit details, or sensitive runtime artifacts in public issues.

If a report requires sensitive details, contact the project owner privately where possible and share only the minimum needed to reproduce the issue.

## Security boundaries

SCLite must not:

- publish raw stdout/stderr from real runs;
- include credentials, cookies, bearer tokens, private headers, or private paths in examples;
- claim legal authorization for target testing;
- claim live vulnerability evidence from validation receipts;
- turn schema validation into permission to execute tools;
- become a protocol adapter or execution wrapper.

## Public-safe fixture requirements

Fixtures should be synthetic or explicitly public-safe. They should preserve clear non-claims and be reviewable without live targets, private operator state, or external services.
