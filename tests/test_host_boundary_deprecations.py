from __future__ import annotations

import pytest

from sclite.hosts import extract_host
from sclite.redaction import sanitize_public_artifact


def test_host_parsing_and_sanitizing_are_explicit_legacy_helpers() -> None:
    with pytest.deprecated_call(match="normalize targets in the host"):
        assert extract_host("https://example.com") == "example.com"
    with pytest.deprecated_call(match="not publication authority"):
        assert sanitize_public_artifact({"token": "secret"}) == {"token": "<redacted>"}
