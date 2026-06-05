from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOVENGINE_BUNDLE = ROOT / 'examples' / 'govengine-integration'


def test_govengine_stable_import_surface() -> None:
    from sclite.bundles import materialize_review_bundle, review_bundle, validate_review_bundle_shape
    from sclite.integrity import artifact_descriptor, verify_artifact_chain_manifest
    from sclite.profiles import validate_carrier_profile_ref, validate_trust_profile_ref
    from sclite.review import build_review_record_from_manifest
    from sclite.scope_fidelity import build_lifecycle_scope_fidelity_report
    from sclite.tickets import validate_ticket_semantics, verify_ticket_use

    assert callable(artifact_descriptor)
    assert callable(verify_artifact_chain_manifest)
    assert callable(validate_ticket_semantics)
    assert callable(verify_ticket_use)
    assert callable(build_review_record_from_manifest)
    assert callable(review_bundle)
    assert callable(materialize_review_bundle)
    assert callable(validate_review_bundle_shape)
    assert callable(validate_trust_profile_ref)
    assert callable(validate_carrier_profile_ref)
    assert callable(build_lifecycle_scope_fidelity_report)


def test_govengine_fixture_contract_smoke() -> None:
    from sclite.bundles import review_bundle
    from sclite.profiles import validate_carrier_profile_ref, validate_trust_profile_ref

    record = review_bundle(GOVENGINE_BUNDLE, generated_at='2026-06-01T00:00:00+00:00')
    assert record['verdict'] == 'pass'
    assert record['summary']['root_chain_digest']

    ticket = json.loads((GOVENGINE_BUNDLE / '04_execution_ticket.json').read_text(encoding='utf-8'))
    trust = json.loads((GOVENGINE_BUNDLE / 'trust_profile_ref.json').read_text(encoding='utf-8'))
    carrier = json.loads((GOVENGINE_BUNDLE / 'carrier_profile_ref.json').read_text(encoding='utf-8'))
    assert 'trust_profile_subject_digest_bound' in validate_trust_profile_ref(trust, ticket)
    assert 'carrier_profile_subject_digest_bound' in validate_carrier_profile_ref(carrier, ticket)


def test_govengine_fixture_cli_contract_smoke() -> None:
    commands = [
        ['validate-chain', str(GOVENGINE_BUNDLE / 'artifact_chain_manifest.json'), '--strict-lifecycle'],
        ['verify-lifecycle', str(GOVENGINE_BUNDLE / 'artifact_chain_manifest.json')],
        ['review', str(GOVENGINE_BUNDLE), '--format', 'summary', '--fail-on', 'review'],
        [
            'validate-trust-profile',
            str(GOVENGINE_BUNDLE / 'trust_profile_ref.json'),
            '--subject',
            str(GOVENGINE_BUNDLE / '04_execution_ticket.json'),
        ],
        [
            'validate-carrier-profile',
            str(GOVENGINE_BUNDLE / 'carrier_profile_ref.json'),
            '--subject',
            str(GOVENGINE_BUNDLE / '04_execution_ticket.json'),
        ],
    ]

    for command in commands:
        proc = subprocess.run(
            [sys.executable, '-m', 'sclite.cli', *command],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
