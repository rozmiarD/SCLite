# Contributing to SCLite

SCLite is a small Security Contract Layer package. Keep the core intentionally narrow:

```text
define / validate / hash / bind / redact / review / verify
```

## Development setup

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m pytest -q
```

## Boundary rules

SCLite must not become:

- a scanner;
- an executor;
- a sandbox;
- a full policy engine;
- a protocol/carrier adapter;
- a proof of legal authorization;
- a proof of live vulnerability evidence.

New artifacts or helpers should preserve public-safe behavior: schemas and fixtures must not include credentials, private targets, raw runtime logs, cookies, tokens, private paths, or live exploit output.

## Change expectations

For meaningful changes:

- update schemas and fixtures together when a contract changes;
- add or update tests;
- update `CHANGELOG.md`;
- update `SPEC.md` or docs when semantics change;
- run the local validation commands in `PUBLICATION_CHECKLIST.md` before release-oriented work.
