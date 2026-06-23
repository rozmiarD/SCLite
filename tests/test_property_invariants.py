from __future__ import annotations

import random
import string

from sclite.artifacts import artifact_sha256, canonicalize_artifact
from sclite.hosts import extract_host


def test_canonical_json_digest_is_stable_under_object_key_order() -> None:
    rng = random.Random(20260614)
    for _ in range(100):
        keys = ['k' + ''.join(rng.choice(string.ascii_lowercase) for _ in range(6)) for _ in range(8)]
        value = {key: {'n': index, 'items': [key, index]} for index, key in enumerate(keys)}
        shuffled = list(value.items())
        rng.shuffle(shuffled)

        assert canonicalize_artifact(value) == canonicalize_artifact(dict(shuffled))
        assert artifact_sha256(value) == artifact_sha256(dict(shuffled))


def test_host_extraction_normalizes_common_wrappers_without_authorizing_scope() -> None:
    samples = [
        ('HOST: Example.COM', 'example.com'),
        ('origin: https://Sub.Example.COM/path', 'sub.example.com'),
        ('https://userinfo@Example.COM:443/path', 'example.com'),
        ('*.Example.COM', 'example.com'),
        ('not a host', ''),
        ('localhost', ''),
        ('user@example.com', ''),
    ]

    for raw, expected in samples:
        assert extract_host(raw) == expected
