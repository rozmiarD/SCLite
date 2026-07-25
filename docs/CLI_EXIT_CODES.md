# CLI Exit Codes

SCLite CLI commands use predictable exit codes for CI and controlled consumer
integrations.

## Contract

- `0` — command completed and the requested validation/review did not reach the configured failure threshold.
- `1` — invalid input, malformed artifact, failed schema validation, failed chain verification, failed ticket-use verification, failed profile binding, or invalid review-bundle shape.
- `2` — command-line usage error, missing required arguments, or a review verdict reached the configured `--fail-on` threshold.

## Review thresholds

Commands with `--fail-on` support `none`, `fail`, or `review`:

```bash
sclite-devtools scope-fidelity --fail-on review ...
sclite-devtools review-lifecycle --fail-on review ...
sclite review --fail-on review ...
```

- `--fail-on none`: `review` and `fail` verdicts still exit `0`; callers must inspect JSON.
- `--fail-on fail`: only `fail` returns `2`.
- `--fail-on review`: both `review` and `fail` return `2`.

Use `--format json` when a caller needs machine-readable detail.

## Integration guidance

Controlled consumer CI can use:

```bash
sclite review examples/govengine-integration --format json --fail-on review
sclite review examples/bad-review-bundle-cross-host --format json --fail-on review
```

The first should exit `0`; the second should exit `2` because the fixture intentionally contains cross-role target drift.

A non-zero CLI result is not proof of unsafe live execution; it means the local SCLite artifact/review gate did not pass the requested threshold.
