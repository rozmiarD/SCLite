# SCLite bad review bundle: cross-host fixture

This fixture intentionally introduces cross-role target drift: policy references `evil.example.net` while the execution contract/ticket target remains `example.com`. It exists for downstream negative tests. Expected review verdict: `fail`.

```bash
sclite review examples/bad-review-bundle-cross-host --format json
```
