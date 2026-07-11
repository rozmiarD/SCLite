from __future__ import annotations

import json
import shutil
import os
from pathlib import Path

import pytest

from sclite import ChainVerificationError, VerificationLimits, verify_artifact_chain_manifest
from sclite._json import _JsonBudget, load_json_object, parse_json_object


class InputError(ValueError):
    pass


ROOT = Path(__file__).resolve().parents[1]
CHAIN_FIXTURE = ROOT / 'examples' / 'govengine-integration'


@pytest.mark.parametrize(
    'payload',
    [
        '{"scope":"first","scope":"second"}',
        '{"outer":{"scope":"first","sc\\u006fpe":"second"}}',
    ],
)
def test_strict_parser_rejects_duplicate_keys_at_every_depth(payload: str) -> None:
    with pytest.raises(InputError, match="duplicate object key 'scope'"):
        parse_json_object(payload, source='inline', error_cls=InputError)


@pytest.mark.parametrize('constant', ['NaN', 'Infinity', '-Infinity'])
def test_strict_parser_rejects_non_standard_numbers(constant: str) -> None:
    with pytest.raises(InputError, match='non-standard number'):
        parse_json_object(f'{{"value":{constant}}}', source='inline', error_cls=InputError)


def test_parser_rejects_finite_overflow_and_surrogate(tmp_path: Path) -> None:
    overflow = tmp_path / 'overflow.json'
    overflow.write_bytes(b'{"value":1e10000}')
    with pytest.raises(InputError, match='not finite'):
        load_json_object(overflow, error_cls=InputError)
    surrogate = tmp_path / 'surrogate.json'
    surrogate.write_bytes(b'{"value":"\\ud800"}')
    with pytest.raises(InputError, match='invalid Unicode surrogate'):
        load_json_object(surrogate, error_cls=InputError)


@pytest.mark.skipif(not hasattr(os, 'mkfifo'), reason='FIFO unavailable')
def test_loader_rejects_fifo_without_blocking(tmp_path: Path) -> None:
    path = tmp_path / 'blocking.json'
    os.mkfifo(path)
    with pytest.raises(InputError, match='not a regular file'):
        load_json_object(path, error_cls=InputError)


def test_file_byte_limit_accepts_boundary_and_rejects_next_byte(tmp_path: Path) -> None:
    path = tmp_path / 'value.json'
    path.write_bytes(b'{"a":1}')
    boundary = VerificationLimits(max_file_bytes=7, max_total_bytes=7)
    assert load_json_object(path, error_cls=InputError, limits=boundary) == {'a': 1}

    path.write_bytes(b'{"a":1} ')
    with pytest.raises(InputError, match='max_file_bytes=7'):
        load_json_object(path, error_cls=InputError, limits=boundary)


def test_aggregate_byte_budget_spans_multiple_documents(tmp_path: Path) -> None:
    limits = VerificationLimits(max_file_bytes=8, max_total_bytes=13)
    budget = _JsonBudget(limits)
    first = tmp_path / 'first.json'
    second = tmp_path / 'second.json'
    first.write_text('{"a":1}', encoding='utf-8')
    second.write_text('{"b":2}', encoding='utf-8')

    assert load_json_object(first, error_cls=InputError, limits=limits, budget=budget)
    with pytest.raises(InputError, match='max_total_bytes=13'):
        load_json_object(second, error_cls=InputError, limits=limits, budget=budget)


def test_structure_limits_cover_depth_and_node_count() -> None:
    depth_limits = VerificationLimits(max_nesting_depth=3)
    assert parse_json_object(
        '{"a":{"b":1}}',
        source='inline',
        error_cls=InputError,
        limits=depth_limits,
    )
    with pytest.raises(InputError, match='max_nesting_depth=3'):
        parse_json_object(
            '{"a":{"b":{"c":1}}}',
            source='inline',
            error_cls=InputError,
            limits=depth_limits,
        )

    node_limits = VerificationLimits(max_nodes=3)
    assert parse_json_object(
        '{"a":1,"b":2}',
        source='inline',
        error_cls=InputError,
        limits=node_limits,
    )
    with pytest.raises(InputError, match='max_nodes=3'):
        parse_json_object(
            '{"a":1,"b":2,"c":3}',
            source='inline',
            error_cls=InputError,
            limits=node_limits,
        )


def test_verification_limits_reject_invalid_configuration() -> None:
    with pytest.raises(ValueError, match='max_file_bytes must be a positive integer'):
        VerificationLimits(max_file_bytes=0)
    with pytest.raises(ValueError, match='max_total_bytes must be greater'):
        VerificationLimits(max_file_bytes=10, max_total_bytes=9)


def test_cli_input_loader_rejects_duplicate_keys(tmp_path: Path) -> None:
    path = tmp_path / 'artifact.json'
    path.write_text('{"artifact_type":"one","artifact_type":"two"}', encoding='utf-8')

    from sclite._cli_impl import _load_json_object as cli_load_json_object

    with pytest.raises(ValueError, match='duplicate object key'):
        cli_load_json_object(path)


def test_standard_json_roundtrip_is_unchanged() -> None:
    payload = {'nested': {'values': [True, False, None, 1, 'text']}}
    assert parse_json_object(
        json.dumps(payload),
        source='inline',
        error_cls=InputError,
    ) == payload


def test_chain_rejects_duplicate_key_before_descriptor_verification(tmp_path: Path) -> None:
    bundle = tmp_path / 'bundle'
    shutil.copytree(CHAIN_FIXTURE, bundle)
    manifest = json.loads((bundle / 'artifact_chain_manifest.json').read_text(encoding='utf-8'))
    artifact_path = bundle / str(manifest['entries'][0]['path'])
    text = artifact_path.read_text(encoding='utf-8')
    artifact_path.write_text(
        text.replace(
            '"artifact_type": "intent_contract",',
            '"artifact_type": "spoofed",\n  "artifact_type": "intent_contract",',
            1,
        ),
        encoding='utf-8',
    )

    with pytest.raises(ChainVerificationError, match='duplicate object key'):
        verify_artifact_chain_manifest(manifest, root=bundle)


def test_chain_enforces_aggregate_bytes_across_artifacts() -> None:
    manifest = json.loads(
        (CHAIN_FIXTURE / 'artifact_chain_manifest.json').read_text(encoding='utf-8')
    )
    artifact_sizes = [
        (CHAIN_FIXTURE / str(entry['path'])).stat().st_size for entry in manifest['entries']
    ]
    limits = VerificationLimits(
        max_file_bytes=max(artifact_sizes),
        max_total_bytes=sum(artifact_sizes) - 1,
    )

    with pytest.raises(ChainVerificationError, match='aggregate JSON bytes'):
        verify_artifact_chain_manifest(
            manifest,
            root=CHAIN_FIXTURE,
            verification_limits=limits,
        )


def test_chain_enforces_defaultable_manifest_entry_budget() -> None:
    manifest = json.loads(
        (CHAIN_FIXTURE / 'artifact_chain_manifest.json').read_text(encoding='utf-8')
    )
    limits = VerificationLimits(max_manifest_entries=len(manifest['entries']) - 1)

    with pytest.raises(ChainVerificationError, match='max_manifest_entries'):
        verify_artifact_chain_manifest(
            manifest,
            root=CHAIN_FIXTURE,
            verification_limits=limits,
        )
