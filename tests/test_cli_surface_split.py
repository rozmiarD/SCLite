from __future__ import annotations

import ast
from pathlib import Path

from sclite import devtools, kernel_cli
from sclite import _cli_impl


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_COMMANDS = {
    'validate-artifact', 'hash-artifact', 'validate-chain', 'verify-lifecycle',
    'verify-guarded-chain', 'verify-secure-bundle', 'validate-ticket',
    'explain-ticket', 'verify-ticket-use', 'validate-trust-profile',
    'validate-carrier-profile', 'redaction-policy', 'redaction-receipt',
    'validation-surface-index', 'snapshot-manifest', 'scope-fidelity',
    'review-lifecycle', 'review', 'export-review-bundle',
}


def test_cli_command_classification_is_complete() -> None:
    assert _cli_impl.KERNEL_COMMANDS.isdisjoint(_cli_impl.DEVTOOLS_COMMANDS)
    assert _cli_impl.KERNEL_COMMANDS | _cli_impl.DEVTOOLS_COMMANDS == EXPECTED_COMMANDS


def test_kernel_entrypoint_rejects_devtools_command(capsys) -> None:
    assert kernel_cli.main(['redaction-policy']) == 2
    assert 'use sclite-devtools' in capsys.readouterr().err


def test_devtools_entrypoint_rejects_kernel_command(capsys) -> None:
    assert devtools.main(['validate-chain']) == 2
    assert 'use sclite' in capsys.readouterr().err


def test_legacy_cli_module_is_removed() -> None:
    assert not (ROOT / 'sclite/cli.py').exists()


def test_production_modules_do_not_import_testing_namespace() -> None:
    for source in sorted((ROOT / 'sclite').glob('*.py')):
        if source.name == 'testing.py':
            continue
        tree = ast.parse(source.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.module not in {'testing', 'sclite.testing'}
