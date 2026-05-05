from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from . import artifacts as scl


RECEIPT_ARTIFACT_TYPE = 'security_contract_validation_receipt'
RECEIPT_SCHEMA_VERSION = 'v0.1'
RECEIPT_SCHEMA_REF = 'schemas/security_contract_validation_receipt.v0.1.schema.json'
VALIDATED_TRACE = 'scope/input -> policy decision -> prepared execution spec -> approved execution spec -> dry-run execution receipt -> evidence summary'

ReceiptSchemaValidationError = scl.JsonSchemaValidationError


@dataclass(frozen=True)
class CheckReceipt:
    check_id: str
    description: str
    status: str
    command: List[str]
    cwd_label: str
    returncode: int
    duration_seconds: float
    stdout_excerpt: str
    stderr_excerpt: str


def package_root() -> Path:
    return Path(__file__).resolve().parent


def repo_root() -> Path:
    """Compatibility alias for callers that validate from the current source tree."""
    return package_root().parents[0]


def _load_json(path: Path) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise scl.JsonSchemaValidationError(f'{path}: JSON root is not an object')
    return value


def load_fixture_artifacts(fixture_dir: Path) -> Dict[str, Any]:
    artifacts: Dict[str, Any] = {}
    for filename in scl.PROOF_TRACE_FILES:
        path = fixture_dir / filename
        if not path.exists():
            raise FileNotFoundError(f'missing fixture artifact: {path}')
        if filename.endswith('.md'):
            artifacts[filename] = path.read_text(encoding='utf-8')
        else:
            artifacts[filename] = _load_json(path)
    return artifacts


def _fixture_forbidden_values() -> List[str]:
    redacted_session_marker = 'session' + '=<redacted>'
    old_workspace_marker = '<workspace' + '_path_redacted>'
    old_cookie_marker = '<cookie' + '_redacted>'
    operator_marker = 'operator' + '_supplied'
    bug_bounty_header = 'X-Bug' + '-Bounty'
    test_account_header = 'X-Test' + '-Account-Email'
    auth_header = 'Author' + 'ization:'
    bearer_prefix = 'Bearer' + ' '
    return [
        str(Path.home()),
        'private-researcher-handle',
        'private.txt',
        'session=abc',
        redacted_session_marker,
        old_workspace_marker,
        old_cookie_marker,
        operator_marker,
        bug_bounty_header,
        test_account_header,
        auth_header,
        bearer_prefix,
    ]


def validate_fixture_dir(fixture_dir: Path, *, schema_root: Path | None = None) -> List[str]:
    errors: List[str] = []
    try:
        artifacts = load_fixture_artifacts(fixture_dir)
    except Exception as exc:
        return [f'load_failed:{exc}']

    errors.extend(scl.validate_public_proof_trace_artifacts(artifacts))

    manifest = scl.proof_trace_manifest()
    for filename in scl.PROOF_TRACE_FILES:
        metadata = manifest.get(filename) or {}
        schema_ref = str(metadata.get('schema') or '')
        if not schema_ref:
            continue
        try:
            scl.validate_schema_ref(schema_ref, artifacts[filename], root=schema_root or Path.cwd())
        except Exception as exc:
            errors.append(f'{filename}:schema_validation:{exc}')

    serialized = '\n'.join(
        value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)
        for value in artifacts.values()
    )
    for needle in _fixture_forbidden_values():
        if needle and needle in serialized:
            errors.append(f'forbidden_value_present:{needle}')
    return errors


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _excerpt(text: str, limit: int = 1600) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + '\n...[truncated]'


def validate_receipt_schema(receipt: Mapping[str, Any], *, schema_root: Path | None = None) -> None:
    scl.validate_schema_ref(RECEIPT_SCHEMA_REF, receipt, root=schema_root or Path.cwd())


def build_validation_receipt(checks: Sequence[CheckReceipt], *, checks_requested: Sequence[str] | None = None) -> Dict[str, Any]:
    failed = [check for check in checks if check.status != 'passed']
    requested = list(checks_requested) if checks_requested is not None else [check.check_id for check in checks]
    receipt = {
        'artifact_type': RECEIPT_ARTIFACT_TYPE,
        'schema_version': RECEIPT_SCHEMA_VERSION,
        'schema_ref': RECEIPT_SCHEMA_REF,
        'generated_at': _utc_now(),
        'status': 'passed' if not failed else 'failed',
        'scope': {
            'mode': 'local_public_safe_validation',
            'live_target_execution': False,
            'protocol_adapter_work': False,
            'public_push': False,
        },
        'validated_trace': VALIDATED_TRACE,
        'checks_requested': requested,
        'checks_passed': [check.check_id for check in checks if check.status == 'passed'],
        'checks_failed': [check.check_id for check in failed],
        'checks': [asdict(check) for check in checks],
        'summary': {
            'total': len(checks),
            'passed': len(checks) - len(failed),
            'failed': len(failed),
        },
    }
    validate_receipt_schema(receipt)
    return receipt


def _print_markdown(receipt: Mapping[str, Any]) -> None:
    print('# Security Contract Validation Receipt')
    print('')
    print(f"status: `{receipt['status']}`")
    print(f"generated_at: `{receipt['generated_at']}`")
    print(f"trace: `{receipt['validated_trace']}`")
    print('')
    print('## Checks')
    for check in receipt['checks']:
        marker = 'OK' if check['status'] == 'passed' else 'FAIL'
        print(f"- {marker} `{check['check_id']}` ({check['duration_seconds']}s)")


def validate_fixture_main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description='Validate public Security Contract Layer fixtures.')
    parser.add_argument('fixture_dir', nargs='?', default=str(package_root() / 'examples' / 'security-contract-proof'))
    args = parser.parse_args(argv)
    fixture_path = Path(str(args.fixture_dir))
    fixture_dir = fixture_path if fixture_path.is_absolute() else (Path.cwd() / fixture_path).resolve()
    errors = validate_fixture_dir(fixture_dir)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f'security_contract_fixtures_ok:{fixture_dir}')
    return 0


def validation_receipt_main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description='Validate a local/public-safe SCL proof fixture and emit a receipt.')
    parser.add_argument('fixture_dir', nargs='?', default=str(package_root() / 'examples' / 'security-contract-proof'))
    parser.add_argument('--format', choices=['json', 'markdown'], default='json', help='receipt output format')
    args = parser.parse_args(argv)

    started = time.monotonic()
    fixture_path = Path(str(args.fixture_dir))
    fixture_dir = fixture_path if fixture_path.is_absolute() else (Path.cwd() / fixture_path).resolve()
    errors = validate_fixture_dir(fixture_dir)
    status = 'passed' if not errors else 'failed'
    check = CheckReceipt(
        check_id='fixture_validation',
        description='Validate SCL proof fixture artifacts against schemas, invariants, and clean-fixture rules.',
        status=status,
        command=['scl', 'validate', str(fixture_dir)],
        cwd_label='.',
        returncode=0 if status == 'passed' else 1,
        duration_seconds=round(time.monotonic() - started, 3),
        stdout_excerpt='' if errors else f'security_contract_fixtures_ok:{fixture_dir}',
        stderr_excerpt='\n'.join(errors),
    )
    receipt = build_validation_receipt([check], checks_requested=['fixture_validation'])
    if args.format == 'markdown':
        _print_markdown(receipt)
    else:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt['status'] == 'passed' else 1
