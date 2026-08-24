from __future__ import annotations

import hashlib
import hmac
import importlib.resources
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from sclite.artifacts import (
    CanonicalizationError,
    artifact_sha256,
    artifact_sha256_v2,
    canonicalize_artifact,
    canonicalize_artifact_v2,
)


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


def test_frozen_v0_1_vectors_and_digests_are_preserved() -> None:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    assert corpus["canonicalization"] == [
        {
            "id": "unicode",
            "value": {"text": "Zażółć gęślą 🛡️", "nested": {"β": "é"}},
            "canonical": '{"nested":{"β":"é"},"text":"Zażółć gęślą 🛡️"}',
            "sha256": "0b2ab5dc01aa40bc0542ddd7bf005fb09a48ae27395c845c405c47984c9308eb",
        },
        {
            "id": "numbers",
            "value": {"zero": 0, "negative": -17, "fraction": 1.25},
            "canonical": '{"fraction":1.25,"negative":-17,"zero":0}',
            "sha256": "abe44cfee7fa44f3d138e868912b6572d561dd1422154b44d231da08e7feff92",
        },
    ]
    assert corpus["chain"]["sha256"] == "b4e54121524fa0c8adc8ac4b23bc1c3ba3929fe8eecf2f6042f1380f556ca172"


def _python_v2_result(item: dict[str, object]) -> dict[str, str]:
    value = item["value"] if "value" in item else float(str(item["input"]))
    try:
        canonical = canonicalize_artifact_v2(value)
    except CanonicalizationError as error:
        return {"id": str(item["id"]), "status": "rejected", "reason_code": error.reason_code}
    return {
        "id": str(item["id"]),
        "status": "accepted",
        "canonical": canonical,
        "sha256": artifact_sha256_v2(value),
    }


def test_python_matches_versioned_numeric_v2_corpus() -> None:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    for item in corpus["numeric_canonicalization_v0_2"]:
        result = _python_v2_result(item)
        assert result["status"] == item["status"]
        if result["status"] == "accepted":
            assert result["canonical"] == item["canonical"]
            assert result["sha256"] == item["sha256"]
        else:
            assert result["reason_code"] == item["reason_code"]


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


def test_python_and_javascript_agree_for_every_v2_numeric_vector() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not installed")
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    result = subprocess.run(
        [node, str(ROOT / "scripts/verify_vectors.mjs"), str(CORPUS), "--v2-results"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [
        _python_v2_result(item) for item in corpus["numeric_canonicalization_v0_2"]
    ]


def test_corpus_is_available_from_installed_package_resources() -> None:
    resource = importlib.resources.files("sclite.conformance").joinpath(
        "sclite-2.0-vectors.json"
    )
    packaged = resource.read_text(encoding="utf-8")
    assert json.loads(packaged)["schema"] == "sclite.conformance.v2"
    assert packaged == CORPUS.read_text(encoding="utf-8")
