from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_TRUE_KEYS = {
    'runtime_authorized',
    'legal_authorization_proven',
    'pki_verified',
    'carrier_delivery_verified',
    'live_execution_verified',
    'trust_decision_proven',
}
PUBLIC_JSON_ROOTS = [ROOT / 'examples', ROOT / 'sclite' / 'examples']


def _walk(value: Any, path: str = '') -> list[str]:
    failures: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child_path = f'{path}.{key}' if path else str(key)
            if key in FORBIDDEN_TRUE_KEYS and item is True:
                failures.append(child_path)
            failures.extend(_walk(item, child_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            failures.extend(_walk(item, f'{path}[{index}]'))
    return failures


def test_public_fixtures_do_not_claim_runtime_authority() -> None:
    failures: list[str] = []
    for root in PUBLIC_JSON_ROOTS:
        for path in sorted(root.rglob('*.json')):
            value = json.loads(path.read_text(encoding='utf-8'))
            for failure in _walk(value):
                failures.append(f'{path.relative_to(ROOT)}:{failure}')
    assert failures == []


def test_review_records_preserve_required_non_claims() -> None:
    required = {
        'does_not_execute_tools',
        'does_not_prove_legal_authorization',
        'does_not_prove_signer_identity',
        'does_not_prove_carrier_delivery',
        'does_not_replace_runtime_policy_decision',
    }
    records = list((ROOT / 'examples').rglob('verification_receipt.json')) + list((ROOT / 'examples').rglob('review_record.json'))
    assert records
    for path in records:
        record = json.loads(path.read_text(encoding='utf-8'))
        if record.get('artifact_type') == 'review_record':
            assert required <= set(record.get('non_claims') or []), path
