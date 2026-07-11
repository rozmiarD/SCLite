from __future__ import annotations

import ast
from pathlib import Path

from sclite import cli, devtools, kernel_cli


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
    assert cli.KERNEL_COMMANDS.isdisjoint(cli.DEVTOOLS_COMMANDS)
    assert cli.KERNEL_COMMANDS | cli.DEVTOOLS_COMMANDS == EXPECTED_COMMANDS


def test_kernel_entrypoint_rejects_devtools_command(capsys) -> None:
    assert kernel_cli.main(['redaction-policy']) == 2
    assert 'use sclite-devtools' in capsys.readouterr().err


def test_devtools_entrypoint_rejects_kernel_command(capsys) -> None:
    assert devtools.main(['validate-chain']) == 2
    assert 'use sclite' in capsys.readouterr().err


def test_legacy_cli_alias_warns_but_remains_compatible(capsys) -> None:
    assert cli.main(['redaction-policy']) == 0
    captured = capsys.readouterr()
    assert 'deprecated_cli_alias:redaction-policy' in captured.err
    assert 'redaction_policy' in captured.out


def test_production_modules_do_not_import_testing_namespace() -> None:
    for source in sorted((ROOT / 'sclite').glob('*.py')):
        if source.name == 'testing.py':
            continue
        tree = ast.parse(source.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.module not in {'testing', 'sclite.testing'}
