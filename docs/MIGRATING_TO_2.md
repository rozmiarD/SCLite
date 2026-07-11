# Migrating to SCLite 2.0

SCLite 2.0 removes the orchestration-specific reaction, trigger, watchdog and
automation modules and schemas. RExecOp owns those contracts. Replace imports
using [`import-map-2.0.json`](import-map-2.0.json) or run:

```bash
python scripts/codemod_imports_2.py path/to/source.py
```

The codemod rewrites module imports only. Review top-level multi-symbol imports
manually and use `rexecop.contracts.orchestration` for owner builders.

`legacy_public_safe` and per-item `public_safe` booleans are removed. Consume
the structured `disclosure.status`, `disclosure.checks`, `disclosure.coverage`
and `publication_authorized` fields instead. SCLite never infers publication
authorization from a boolean.

Domain schemas must be supplied explicitly through an immutable
`SchemaResolver`. SCLite does not auto-load plugins or old built-ins. Historical
v0.1 orchestration artifacts remain readable through RExecOp's owner resolver.
