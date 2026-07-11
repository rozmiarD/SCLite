from __future__ import annotations

import hashlib
import hmac
import importlib.resources
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from sclite.artifacts import artifact_sha256, canonicalize_artifact


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "conformance/sclite-2.0-vectors.json"


def test_python_matches_language_neutral_positive_corpus() -> None:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    for item in corpus["canonicalization"]:
        assert canonicalize_artifact(item["value"]) == item["canonical"]
        assert artifact_sha256(item["value"]) == item["sha256"]
    assert artifact_sha256(corpus["chain"]["payload"]) == corpus["chain"]["sha256"]
    guard = corpus["guard"]
    tag = hmac.new(
        guard["key_utf8"].encode(),
        canonicalize_artifact(guard["payload"]).encode(),
        hashlib.sha256,
    ).hexdigest()
    assert tag == guard["hmac_sha256"]


def test_independent_javascript_harness_matches_entire_corpus() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not installed")
    result = subprocess.run(
        [node, str(ROOT / "scripts/verify_vectors.mjs"), str(CORPUS)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "sclite_vectors_ok:javascript"


def test_corpus_is_available_from_installed_package_resources() -> None:
    resource = importlib.resources.files("sclite.conformance").joinpath(
        "sclite-2.0-vectors.json"
    )
    assert json.loads(resource.read_text(encoding="utf-8"))["schema"] == "sclite.conformance.v2"
