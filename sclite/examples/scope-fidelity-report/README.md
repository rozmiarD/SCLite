# Scope Fidelity Report fixture

This clean synthetic fixture shows the SCL v0.1 static host-binding review artifact.

It compares the approved-spec target host with hosts detected in normalized arguments and execution-plan steps. It is static analysis only: no DNS resolution, no redirect following, no live target execution, and no authorization claim.

Validate it with:

```bash
python -m sclite.kernel_cli validate-artifact --schema scope_fidelity_report.v0.1 examples/scope-fidelity-report/scope_fidelity_report.json
```
