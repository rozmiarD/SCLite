from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Sequence

from .artifacts import build_artifact_hash, validate_artifact
from .integrity import ChainVerificationError, verify_artifact_chain_manifest
from .redaction import build_default_redaction_policy, build_redaction_receipt
from .scope_fidelity import build_scope_fidelity_report, build_scope_fidelity_report_from_approved_spec, validate_scope_fidelity_report
from .surfaces import build_public_snapshot_manifest, build_public_validation_surface_index
from .validation import package_root, validate_fixture_dir, validation_receipt_main


def _load_json_object(path: Path) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError(f'{path}: JSON root is not an object')
    return value


def _scope_fidelity_exit_code(verdict: str, fail_on: str) -> int:
    if fail_on == 'none':
        return 0
    if fail_on == 'fail' and verdict == 'fail':
        return 2
    if fail_on == 'review' and verdict in {'review', 'fail'}:
        return 2
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Security Contract Layer validation CLI.')
    sub = parser.add_subparsers(dest='command', required=True)

    validate_cmd = sub.add_parser('validate', help='validate a public-safe SCL proof fixture directory')
    validate_cmd.add_argument('fixture_dir', nargs='?', default=str(package_root() / 'examples' / 'security-contract-proof'))

    artifact_cmd = sub.add_parser('validate-artifact', help='validate one JSON artifact against an SCL schema')
    artifact_cmd.add_argument('--schema', required=True, help='schema name or schema path, for example approved_execution_spec.v0.1')
    artifact_cmd.add_argument('artifact', help='path to a JSON artifact')

    hash_cmd = sub.add_parser('hash-artifact', help='emit a deterministic canonical JSON SHA-256 descriptor for one artifact')
    hash_cmd.add_argument('artifact', help='path to a JSON artifact')
    hash_cmd.add_argument('--schema', help='optional schema name/path to validate before hashing')
    hash_cmd.add_argument('--format', choices=['json', 'digest'], default='json')

    chain_cmd = sub.add_parser('validate-chain', help='verify a v0.2 lifecycle artifact-chain manifest')
    chain_cmd.add_argument('manifest', help='path to artifact_chain_manifest.json')
    chain_cmd.add_argument('--root', help='artifact root directory; defaults to the manifest directory')
    chain_cmd.add_argument('--no-schema', action='store_true', help='skip schema validation while checking hashes/links')
    chain_cmd.add_argument('--format', choices=['json', 'summary'], default='summary')

    lifecycle_cmd = sub.add_parser('verify-lifecycle', help='verify a v0.2 contract lifecycle manifest')
    lifecycle_cmd.add_argument('manifest', help='path to artifact_chain_manifest.json')
    lifecycle_cmd.add_argument('--root', help='artifact root directory; defaults to the manifest directory')
    lifecycle_cmd.add_argument('--no-schema', action='store_true', help='skip schema validation while checking hashes/links')
    lifecycle_cmd.add_argument('--format', choices=['json', 'summary'], default='summary')

    policy_cmd = sub.add_parser('redaction-policy', help='emit the default public-safe RedactionPolicy descriptor')
    policy_cmd.add_argument('--policy-id', default='sclite-public-safe-v0.1')

    redaction_receipt_cmd = sub.add_parser('redaction-receipt', help='emit a RedactionReceipt for a source/redacted JSON pair')
    redaction_receipt_cmd.add_argument('--source-json', required=True)
    redaction_receipt_cmd.add_argument('--redacted-json', required=True)
    redaction_receipt_cmd.add_argument('--policy-json')
    redaction_receipt_cmd.add_argument('--source-label', default='source_artifact')
    redaction_receipt_cmd.add_argument('--redacted-label', default='redacted_artifact')

    surface_cmd = sub.add_parser('validation-surface-index', help='emit the default PublicValidationSurfaceIndex')
    surface_cmd.add_argument('--generated-at')

    snapshot_cmd = sub.add_parser('snapshot-manifest', help='emit a PublicSnapshotManifest over JSON artifact files')
    snapshot_cmd.add_argument('--file', action='append', default=[], help='JSON artifact path; repeatable')
    snapshot_cmd.add_argument('--snapshot-name', default='sclite-public-snapshot')
    snapshot_cmd.add_argument('--snapshot-version', default='v0.1')

    scope_cmd = sub.add_parser('scope-fidelity', help='build a static ScopeFidelityReport from an approved spec or explicit fields')
    scope_cmd.add_argument('--approved-spec', help='path to an approved_execution_spec JSON artifact')
    scope_cmd.add_argument('--target', help='target URL/host when not using --approved-spec')
    scope_cmd.add_argument('--normalized-arg', action='append', default=[], help='argument scalar to inspect; repeatable')
    scope_cmd.add_argument('--plan-step-json', action='append', default=[], help='execution_plan step JSON object; repeatable')
    scope_cmd.add_argument('--target-in-scope', choices=['true', 'false', 'unknown'], default='unknown')
    scope_cmd.add_argument('--source-artifact', default='', help='source artifact label/path for the report')
    scope_cmd.add_argument('--fail-on', choices=['none', 'fail', 'review'], default='fail', help='return exit code 2 when verdict reaches this threshold')
    scope_cmd.add_argument('--format', choices=['json', 'markdown'], default='json')

    receipt_cmd = sub.add_parser('validation-receipt', help='validate an SCL fixture directory and emit a validation receipt')
    receipt_cmd.add_argument('fixture_dir', nargs='?', default=str(package_root() / 'examples' / 'security-contract-proof'))
    receipt_cmd.add_argument('--format', choices=['json', 'markdown'], default='json')

    args = parser.parse_args(argv)
    if args.command == 'validate':
        fixture_dir = Path(str(args.fixture_dir))
        if not fixture_dir.is_absolute():
            fixture_dir = (Path.cwd() / fixture_dir).resolve()
        errors = validate_fixture_dir(fixture_dir)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print(f'security_contract_fixtures_ok:{fixture_dir}')
        return 0

    if args.command == 'validate-artifact':
        artifact_path = Path(str(args.artifact))
        value = json.loads(artifact_path.read_text(encoding='utf-8'))
        validate_artifact(value, str(args.schema))
        print(f'security_contract_artifact_ok:{artifact_path}')
        return 0

    if args.command == 'hash-artifact':
        artifact_path = Path(str(args.artifact))
        value = json.loads(artifact_path.read_text(encoding='utf-8'))
        if args.schema:
            validate_artifact(value, str(args.schema))
        descriptor = build_artifact_hash(value)
        if args.format == 'digest':
            print(descriptor['digest'])
        else:
            print(json.dumps(descriptor, indent=2, sort_keys=True))
        return 0

    if args.command in {'validate-chain', 'verify-lifecycle'}:
        manifest_path = Path(str(args.manifest)).resolve()
        manifest = _load_json_object(manifest_path)
        root = Path(str(args.root)).resolve() if args.root else manifest_path.parent
        try:
            result = verify_artifact_chain_manifest(manifest, root=root, validate_schemas=not args.no_schema)
        except ChainVerificationError as exc:
            print(f'artifact_chain_failed:{exc}', file=sys.stderr)
            return 1
        if args.format == 'json':
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            label = 'lifecycle_ok' if args.command == 'verify-lifecycle' else 'artifact_chain_ok'
            print(f"{label}:{result['entry_count']}:{result['root_chain_digest']}")
        return 0

    if args.command == 'redaction-policy':
        policy = build_default_redaction_policy(policy_id=str(args.policy_id))
        print(json.dumps(policy, indent=2, sort_keys=True))
        return 0

    if args.command == 'redaction-receipt':
        source = _load_json_object(Path(str(args.source_json)))
        redacted = _load_json_object(Path(str(args.redacted_json)))
        policy = _load_json_object(Path(str(args.policy_json))) if args.policy_json else None
        receipt = build_redaction_receipt(
            source,
            redacted,
            policy=policy,
            source_label=str(args.source_label),
            redacted_label=str(args.redacted_label),
        )
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0

    if args.command == 'validation-surface-index':
        index = build_public_validation_surface_index(generated_at=args.generated_at)
        print(json.dumps(index, indent=2, sort_keys=True))
        return 0

    if args.command == 'snapshot-manifest':
        files = []
        for item in args.file:
            path = Path(str(item))
            value = json.loads(path.read_text(encoding='utf-8'))
            artifact_type = value.get('artifact_type') if isinstance(value, dict) else ''
            files.append({'path': str(path), 'artifact_type': str(artifact_type or ''), 'schema': '', 'public_safe': True, 'value': value})
        manifest = build_public_snapshot_manifest(files, snapshot_name=str(args.snapshot_name), snapshot_version=str(args.snapshot_version))
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0

    if args.command == 'scope-fidelity':
        if args.approved_spec:
            approved_path = Path(str(args.approved_spec))
            spec = _load_json_object(approved_path)
            report = build_scope_fidelity_report_from_approved_spec(spec, source_artifact=args.source_artifact or str(approved_path))
        else:
            if not args.target:
                print('scope-fidelity requires --approved-spec or --target', file=sys.stderr)
                return 2
            plan = []
            for item in args.plan_step_json:
                value = json.loads(str(item))
                if not isinstance(value, dict):
                    print('--plan-step-json must decode to a JSON object', file=sys.stderr)
                    return 2
                plan.append(value)
            target_in_scope = None if args.target_in_scope == 'unknown' else args.target_in_scope == 'true'
            report = build_scope_fidelity_report(
                target=str(args.target),
                normalized_args=list(args.normalized_arg or []),
                execution_plan=plan,
                target_in_scope=target_in_scope,
                source_artifact=str(args.source_artifact or 'cli'),
            )
        validate_scope_fidelity_report(report)
        if args.format == 'markdown':
            shape = report['request_shape']
            print('# Scope Fidelity Report')
            print('')
            print(f"verdict: `{report['verdict']}`")
            print(f"target_host: `{report['target_host']}`")
            print(f"match_status: `{shape['target_host_match_status']}`")
            print(f"hygiene_status: `{shape['request_shape_hygiene_status']}`")
            print(f"reason: `{shape['request_shape_hygiene_reason']}`")
        else:
            print(json.dumps(report, indent=2, sort_keys=True))
        return _scope_fidelity_exit_code(str(report['verdict']), str(args.fail_on))

    if args.command == 'validation-receipt':
        forwarded = [str(args.fixture_dir), '--format', args.format]
        return validation_receipt_main(forwarded)

    parser.error('unknown command')
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
