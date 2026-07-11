from __future__ import annotations

import copy
import json
from pathlib import Path

from sclite.profiles import (
    normalized_profile_binding,
    translate_legacy_profile_ref,
    validate_carrier_profile_ref,
    validate_trust_profile_ref,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "sclite" / "examples" / "trust-carrier-profiles"


def _load(name: str) -> dict:
    return json.loads((FIXTURE / name).read_text(encoding="utf-8"))


def _subject() -> dict:
    return json.loads(
        (ROOT / "sclite/examples/scoped-ticket-v0.3/execution_ticket.json").read_text(
            encoding="utf-8"
        )
    )


def test_unknown_namespaces_round_trip_without_core_classification() -> None:
    trust = translate_legacy_profile_ref(_load("trust_profile_ref.json"))
    trust["trust_profile"] = "future.example/custom_verifier@v7"
    validate_trust_profile_ref(trust, _subject())
    assert normalized_profile_binding(trust) == (
        "trust_profile_ref",
        "future.example/custom_verifier@v7",
    )

    carrier = translate_legacy_profile_ref(_load("carrier_profile_ref.json"))
    carrier["carrier_profile"] = "future.example/custom_carrier@v2.4"
    validate_carrier_profile_ref(carrier, _subject())
    assert normalized_profile_binding(carrier)[1] == "future.example/custom_carrier@v2.4"


def test_translation_does_not_imply_public_safety() -> None:
    source = _load("carrier_profile_ref.json")
    translated = translate_legacy_profile_ref(copy.deepcopy(source))
    assert translated["carrier_profile"] == "legacy.sclite/local_file_bundle@v1"
    assert "public_safe" not in json.dumps(translated).lower()
