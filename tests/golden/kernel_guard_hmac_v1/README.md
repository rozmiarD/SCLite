Artifacts in this directory are the compatibility golden vector for
`kernel_guard_hmac_v1`.

The vector freezes the current SCLite canonical JSON and HMAC transcript shape
for the profile:

- `manifest.json` is the canonical public lifecycle manifest under test;
- `kernel_guard_manifest.json` is the expected deterministic sidecar for that
  manifest;
- `key.txt` is a synthetic test-only HMAC key, not a real secret;
- `expected_entry_tags.json` and `expected_root_tag.txt` are hard-coded
  compatibility truth.

If canonicalization, transcript fields, field coercion, or HMAC inputs change,
this vector must fail. Intentional incompatible changes require a new profile
name, for example `kernel_guard_hmac_v2`, not silent edits to this vector.
