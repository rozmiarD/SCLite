from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from sclite.bundles import ReviewBundleError, review_bundle, validate_review_bundle_shape
from sclite.integrity import build_artifact_chain_manifest

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / 'examples' / 'govengine-integration'
BAD_CROSS_HOST = ROOT / 'examples' / 'bad-review-bundle-cross-host'
ROLE_FILES = [
    ('intent_contract', '01_intent_contract.json'),
    ('policy_decision', '02_policy_decision.json'),
    ('execution_contract', '03_execution_contract.json'),
    ('execution_ticket', '04_execution_ticket.json'),
    ('execution_receipt', '05_execution_receipt.json'),
    ('evidence_contract', '06_evidence_contract.json'),
]


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8'))
    assert isinstance(value, dict)
    return value


def _copy_bundle(tmp_path: Path) -> Path:
    target = tmp_path / 'bundle'
    shutil.copytree(BUNDLE, target)
    return target


def _rewrite_manifest(base: Path) -> None:
    artifacts = []
    for role, filename in ROLE_FILES:
        artifacts.append({'role': role, 'path': filename, 'value': _load(base / filename)})
    manifest = build_artifact_chain_manifest(
        artifacts,
        chain_id='unit-test-review-bundle',
        created_at='2026-05-15T22:30:00+00:00',
        profile='unit-test',
    )
    (base / 'artifact_chain_manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def test_review_bundle_rejects_missing_execution_ticket(tmp_path: Path) -> None:
    bundle = _copy_bundle(tmp_path)
    (bundle / '04_execution_ticket.json').unlink()
    with pytest.raises(ReviewBundleError, match='missing review bundle files'):
        validate_review_bundle_shape(bundle)


def test_review_bundle_rejects_wrong_manifest_path_name(tmp_path: Path) -> None:
    bundle = _copy_bundle(tmp_path)
    manifest = _load(bundle / 'artifact_chain_manifest.json')
    manifest['entries'][3]['path'] = 'execution_ticket.json'
    (bundle / 'artifact_chain_manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    with pytest.raises(ReviewBundleError, match='manifest paths do not match'):
        validate_review_bundle_shape(bundle)


def test_review_bundle_rejects_manifest_path_escape(tmp_path: Path) -> None:
    bundle = _copy_bundle(tmp_path)
    manifest = _load(bundle / 'artifact_chain_manifest.json')
    manifest['entries'][0]['path'] = '../01_intent_contract.json'
    (bundle / 'artifact_chain_manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    with pytest.raises(ReviewBundleError, match='manifest paths do not match'):
        review_bundle(bundle)


def _assert_fail_detail(record: dict, expected: str) -> None:
    assert record['verdict'] == 'fail'
    details = ' | '.join(str(check.get('detail') or '') for check in record.get('checks') or [])
    assert expected in details


def test_review_bundle_flags_tampered_artifact_digest(tmp_path: Path) -> None:
    bundle = _copy_bundle(tmp_path)
    intent = _load(bundle / '01_intent_contract.json')
    intent['intent']['summary'] = 'tampered after manifest creation'
    (bundle / '01_intent_contract.json').write_text(json.dumps(intent, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    _assert_fail_detail(review_bundle(bundle), 'descriptor mismatch')


def test_review_bundle_rejects_wrong_role_order(tmp_path: Path) -> None:
    bundle = _copy_bundle(tmp_path)
    manifest = _load(bundle / 'artifact_chain_manifest.json')
    manifest['entries'][3]['role'] = 'execution_contract'
    (bundle / 'artifact_chain_manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    with pytest.raises(ReviewBundleError, match='manifest paths do not match'):
        review_bundle(bundle)


def test_review_bundle_flags_evidence_receipt_link_drift(tmp_path: Path) -> None:
    bundle = _copy_bundle(tmp_path)
    evidence = _load(bundle / '06_evidence_contract.json')
    evidence['links']['execution_receipt']['descriptor']['digest'] = '0' * 64
    (bundle / '06_evidence_contract.json').write_text(json.dumps(evidence, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    _rewrite_manifest(bundle)
    _assert_fail_detail(review_bundle(bundle), 'evidence-receipt digest mismatch')


def test_review_bundle_flags_receipt_ticket_link_drift(tmp_path: Path) -> None:
    bundle = _copy_bundle(tmp_path)
    receipt = _load(bundle / '05_execution_receipt.json')
    receipt['links']['execution_ticket']['descriptor']['digest'] = '0' * 64
    (bundle / '05_execution_receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    _rewrite_manifest(bundle)
    _assert_fail_detail(review_bundle(bundle), 'receipt-ticket digest mismatch')


def test_review_bundle_flags_ticket_execution_contract_binding_drift(tmp_path: Path) -> None:
    bundle = _copy_bundle(tmp_path)
    ticket = _load(bundle / '04_execution_ticket.json')
    ticket['integrity']['ticket_binds_execution_contract_digest'] = '0' * 64
    (bundle / '04_execution_ticket.json').write_text(json.dumps(ticket, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    _rewrite_manifest(bundle)
    _assert_fail_detail(review_bundle(bundle), 'ticket integrity execution_contract digest mismatch')


def test_bad_cross_host_bundle_returns_fail_verdict() -> None:
    record = review_bundle(BAD_CROSS_HOST)
    assert record['verdict'] == 'fail'
    assert record['summary']['scope_fidelity_verdict'] == 'fail'
