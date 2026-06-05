from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Sequence

from ._json import load_json_object, load_json_value, parse_json_object
from .artifacts import build_artifact_hash, validate_artifact
from .bundles import ReviewBundleError, export_review_bundle_markdown, review_bundle, review_bundle_summary
from .integrity import ChainVerificationError, verify_artifact_chain_manifest
from .kernel_guard import KernelGuardError, verify_kernel_guard_manifest
from .profiles import (
    ProfileReferenceError,
    profile_ref_summary,
    validate_carrier_profile_ref,
    validate_trust_profile_ref,
)
from .redaction import build_default_redaction_policy, build_redaction_receipt
from .review import ReviewRecordError, build_review_record_from_manifest, review_record_markdown
from .scope_fidelity import build_scope_fidelity_report, build_scope_fidelity_report_from_approved_spec, validate_scope_fidelity_report
from .secure import SecureBundleError, resolve_guard_path, verify_secure_bundle
from .surfaces import build_public_snapshot_manifest, build_public_validation_surface_index
from .tickets import (
    TicketSemanticError,
    TicketUseVerificationError,
    explain_ticket,
    ticket_summary,
    validate_ticket_schema,
    validate_ticket_semantics,
    verify_ticket_use,
)


class CliInputError(ValueError):
    """Raised when CLI input files or inline JSON cannot be read cleanly."""


def _load_json_object(path: Path) -> Dict[str, Any]:
    return load_json_object(path, error_cls=CliInputError)


def _load_json_value(path: Path) -> Any:
    return load_json_value(path, error_cls=CliInputError)


def _parse_json_object(text: str, *, source: str) -> Dict[str, Any]:
    return parse_json_object(text, source=source, error_cls=CliInputError)


def _scope_fidelity_exit_code(verdict: str, fail_on: str) -> int:
    if fail_on == 'none':
        return 0
    if fail_on == 'fail' and verdict == 'fail':
        return 2
    if fail_on == 'review' and verdict in {'review', 'fail'}:
        return 2
    return 0


def _guard_key_from_env(env_name: str) -> str:
    key = os.environ.get(str(env_name) or '')
    if not key:
        raise SecureBundleError(f'missing guard key env {env_name}')
    return key


def _require_guard_requested(args: Any) -> bool:
    return bool(getattr(args, 'require_guard', False) or getattr(args, 'fail_on_unguarded', False))


def _failed(label: str, exc: BaseException) -> int:
    print(f'{label}:{exc}', file=sys.stderr)
    return 1


def _verify_required_guard_for_manifest(args: Any, manifest_path: Path, *, require_lifecycle: bool) -> Dict[str, Any]:
    guard_path = resolve_guard_path(manifest_path, getattr(args, 'guard', None))
    key = _guard_key_from_env(str(getattr(args, 'guard_key_env', 'SCLITE_KERNEL_GUARD_KEY')))
    if not guard_path.is_file():
        raise SecureBundleError(f'missing kernel guard sidecar: {guard_path}')
    manifest = _load_json_object(manifest_path)
    guard = _load_json_object(guard_path)
    root = Path(str(args.root)).resolve() if getattr(args, 'root', None) else manifest_path.parent
    try:
        return verify_kernel_guard_manifest(
            manifest,
            guard,
            key=key,
            root=root,
            validate_schemas=not getattr(args, 'no_schema', False),
            strict_jsonschema=bool(getattr(args, 'strict_jsonschema', False)),
            require_lifecycle=require_lifecycle,
        )
    except KernelGuardError as exc:
        raise SecureBundleError(str(exc)) from exc


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Security Contract Layer validation CLI.')
    sub = parser.add_subparsers(dest='command', required=True)

    artifact_cmd = sub.add_parser('validate-artifact', help='validate one JSON artifact against an SCL schema')
    artifact_cmd.add_argument('--schema', required=True, help='schema name or schema path, for example execution_contract.v0.2')
    artifact_cmd.add_argument('--strict-jsonschema', action='store_true', help="use Draft 2020-12 validation via the optional 'jsonschema' extra")
    artifact_cmd.add_argument('artifact', help='path to a JSON artifact')

    hash_cmd = sub.add_parser('hash-artifact', help='emit a deterministic canonical JSON SHA-256 descriptor for one artifact')
    hash_cmd.add_argument('artifact', help='path to a JSON artifact')
    hash_cmd.add_argument('--schema', help='optional schema name/path to validate before hashing')
    hash_cmd.add_argument('--format', choices=['json', 'digest'], default='json')

    chain_cmd = sub.add_parser('validate-chain', help='verify a v0.2 lifecycle artifact-chain manifest')
    chain_cmd.add_argument('manifest', help='path to artifact_chain_manifest.json')
    chain_cmd.add_argument('--root', help='artifact root directory; defaults to the manifest directory')
    chain_cmd.add_argument('--no-schema', action='store_true', help='skip artifact schema validation while checking hashes/links')
    chain_cmd.add_argument('--strict-jsonschema', action='store_true', help="use Draft 2020-12 validation via the optional 'jsonschema' extra")
    chain_cmd.add_argument('--strict-lifecycle', action='store_true', help='require the canonical v0.2 lifecycle role sequence with no extras or duplicates')
    chain_cmd.add_argument('--guard', help='path to kernel_guard_manifest.json when --require-guard is used; defaults to manifest directory')
    chain_cmd.add_argument('--guard-key-env', default='SCLITE_KERNEL_GUARD_KEY', help='environment variable containing the HMAC guard key')
    chain_cmd.add_argument('--require-guard', action='store_true', help='fail closed unless a kernel_guard_hmac_v1 sidecar verifies')
    chain_cmd.add_argument('--fail-on-unguarded', action='store_true', help='alias for --require-guard')
    chain_cmd.add_argument('--format', choices=['json', 'summary'], default='summary')

    lifecycle_cmd = sub.add_parser('verify-lifecycle', help='verify a v0.2 contract lifecycle manifest')
    lifecycle_cmd.add_argument('manifest', help='path to artifact_chain_manifest.json')
    lifecycle_cmd.add_argument('--root', help='artifact root directory; defaults to the manifest directory')
    lifecycle_cmd.add_argument('--no-schema', action='store_true', help='skip artifact schema validation while checking hashes/links')
    lifecycle_cmd.add_argument('--strict-jsonschema', action='store_true', help="use Draft 2020-12 validation via the optional 'jsonschema' extra")
    lifecycle_cmd.add_argument('--guard', help='path to kernel_guard_manifest.json when --require-guard is used; defaults to manifest directory')
    lifecycle_cmd.add_argument('--guard-key-env', default='SCLITE_KERNEL_GUARD_KEY', help='environment variable containing the HMAC guard key')
    lifecycle_cmd.add_argument('--require-guard', action='store_true', help='fail closed unless a kernel_guard_hmac_v1 sidecar verifies')
    lifecycle_cmd.add_argument('--fail-on-unguarded', action='store_true', help='alias for --require-guard')
    lifecycle_cmd.add_argument('--format', choices=['json', 'summary'], default='summary')

    guard_cmd = sub.add_parser('verify-guarded-chain', help='verify an optional kernel_guard_hmac_v1 sidecar for an artifact-chain manifest')
    guard_cmd.add_argument('manifest', help='path to artifact_chain_manifest.json')
    guard_cmd.add_argument('--guard', required=True, help='path to kernel_guard_manifest.json')
    guard_cmd.add_argument('--root', help='artifact root directory; defaults to the manifest directory')
    guard_cmd.add_argument('--guard-key-env', default='SCLITE_KERNEL_GUARD_KEY', help='environment variable containing the HMAC guard key')
    guard_cmd.add_argument('--no-schema', action='store_true', help='skip artifact schema validation while checking hashes/links')
    guard_cmd.add_argument('--strict-jsonschema', action='store_true', help="use Draft 2020-12 validation via the optional 'jsonschema' extra")
    guard_cmd.add_argument('--strict-lifecycle', action='store_true', help='require the canonical v0.2 lifecycle role sequence with no extras or duplicates')
    guard_cmd.add_argument('--format', choices=['json', 'summary'], default='summary')

    secure_cmd = sub.add_parser('verify-secure-bundle', help='verify the guarded-strict secure bundle profile')
    secure_cmd.add_argument('target', help='path to artifact_chain_manifest.json or a review_bundle directory')
    secure_cmd.add_argument('--guard', help='path to kernel_guard_manifest.json; defaults to target/manifest directory')
    secure_cmd.add_argument('--root', help='artifact root directory; defaults to the manifest directory')
    secure_cmd.add_argument('--guard-key-env', default='SCLITE_KERNEL_GUARD_KEY', help='environment variable containing the HMAC guard key')
    secure_cmd.add_argument('--no-schema', action='store_true', help='skip artifact schema validation while checking hashes/links')
    secure_cmd.add_argument('--strict-jsonschema', action='store_true', help="use Draft 2020-12 validation via the optional 'jsonschema' extra")
    secure_cmd.add_argument('--format', choices=['json', 'summary'], default='summary')

    ticket_cmd = sub.add_parser('validate-ticket', help='validate an ExecutionTicket and optional execution-contract binding')
    ticket_cmd.add_argument('ticket', help='path to execution_ticket.json')
    ticket_cmd.add_argument('--contract', help='path to execution_contract.json for semantic binding checks')
    ticket_cmd.add_argument('--strict-jsonschema', action='store_true', help="use Draft 2020-12 validation via the optional 'jsonschema' extra")
    ticket_cmd.add_argument('--format', choices=['json', 'summary'], default='summary')

    explain_ticket_cmd = sub.add_parser('explain-ticket', help='explain an ExecutionTicket in reviewer-friendly text')
    explain_ticket_cmd.add_argument('ticket', help='path to execution_ticket.json')

    ticket_use_cmd = sub.add_parser('verify-ticket-use', help='verify receipt/evidence use stays inside a scoped ExecutionTicket')
    ticket_use_cmd.add_argument('ticket', help='path to execution_ticket.json')
    ticket_use_cmd.add_argument('--contract', required=True, help='path to execution_contract.json')
    ticket_use_cmd.add_argument('--receipt', required=True, help='path to execution_receipt.json')
    ticket_use_cmd.add_argument('--evidence-contract', help='path to evidence_contract.json')
    ticket_use_cmd.add_argument('--strict-jsonschema', action='store_true', help="use Draft 2020-12 validation via the optional 'jsonschema' extra")
    ticket_use_cmd.add_argument('--format', choices=['json', 'summary'], default='summary')

    trust_profile_cmd = sub.add_parser('validate-trust-profile', help='validate a digest-bound TrustProfileRef sidecar')
    trust_profile_cmd.add_argument('profile_ref', help='path to trust_profile_ref.json')
    trust_profile_cmd.add_argument('--subject', required=True, help='path to the subject artifact the profile reference binds')
    trust_profile_cmd.add_argument('--strict-jsonschema', action='store_true', help="use Draft 2020-12 validation via the optional 'jsonschema' extra")
    trust_profile_cmd.add_argument('--format', choices=['json', 'summary'], default='summary')

    carrier_profile_cmd = sub.add_parser('validate-carrier-profile', help='validate a digest-bound CarrierProfileRef sidecar')
    carrier_profile_cmd.add_argument('profile_ref', help='path to carrier_profile_ref.json')
    carrier_profile_cmd.add_argument('--subject', required=True, help='path to the subject artifact the profile reference binds')
    carrier_profile_cmd.add_argument('--strict-jsonschema', action='store_true', help="use Draft 2020-12 validation via the optional 'jsonschema' extra")
    carrier_profile_cmd.add_argument('--format', choices=['json', 'summary'], default='summary')

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

    review_cmd = sub.add_parser('review-lifecycle', help='emit a static lifecycle ReviewRecord for an artifact-chain manifest')
    review_cmd.add_argument('manifest', help='path to artifact_chain_manifest.json')
    review_cmd.add_argument('--root', help='artifact root directory; defaults to the manifest directory')
    review_cmd.add_argument('--strict-jsonschema', action='store_true', help="use Draft 2020-12 validation via the optional 'jsonschema' extra")
    review_cmd.add_argument('--guard', help='path to kernel_guard_manifest.json when --require-guard is used; defaults to manifest directory')
    review_cmd.add_argument('--guard-key-env', default='SCLITE_KERNEL_GUARD_KEY', help='environment variable containing the HMAC guard key')
    review_cmd.add_argument('--require-guard', action='store_true', help='fail closed unless a kernel_guard_hmac_v1 sidecar verifies before review')
    review_cmd.add_argument('--fail-on-unguarded', action='store_true', help='alias for --require-guard')
    review_cmd.add_argument('--fail-on', choices=['none', 'fail', 'review'], default='fail')
    review_cmd.add_argument('--format', choices=['json', 'markdown'], default='json')

    bundle_review_cmd = sub.add_parser('review', help='review a canonical SCLite review_bundle directory')
    bundle_review_cmd.add_argument('bundle_dir', help='path to review_bundle directory')
    bundle_review_cmd.add_argument('--strict-jsonschema', action='store_true', help="use Draft 2020-12 validation via the optional 'jsonschema' extra")
    bundle_review_cmd.add_argument('--guard', help='path to kernel_guard_manifest.json when --require-guard is used; defaults to bundle directory')
    bundle_review_cmd.add_argument('--guard-key-env', default='SCLITE_KERNEL_GUARD_KEY', help='environment variable containing the HMAC guard key')
    bundle_review_cmd.add_argument('--require-guard', action='store_true', help='fail closed unless a kernel_guard_hmac_v1 sidecar verifies before review')
    bundle_review_cmd.add_argument('--fail-on-unguarded', action='store_true', help='alias for --require-guard')
    bundle_review_cmd.add_argument('--fail-on', choices=['none', 'fail', 'review'], default='fail')
    bundle_review_cmd.add_argument('--format', choices=['json', 'markdown', 'summary'], default='json')

    export_review_cmd = sub.add_parser('export-review-bundle', help='export a canonical SCLite review_bundle as Markdown or JSON')
    export_review_cmd.add_argument('bundle_dir', help='path to review_bundle directory')
    export_review_cmd.add_argument('--strict-jsonschema', action='store_true', help="use Draft 2020-12 validation via the optional 'jsonschema' extra")
    export_review_cmd.add_argument('--format', choices=['markdown', 'json'], default='markdown')
    export_review_cmd.add_argument('--output', help='write output to this path instead of stdout')

    args = parser.parse_args(argv)
    if args.command == 'validate-artifact':
        artifact_path = Path(str(args.artifact))
        try:
            value = _load_json_value(artifact_path)
            validate_artifact(
                value,
                str(args.schema),
                strict_jsonschema=bool(args.strict_jsonschema),
                allow_external_schema_refs=True,
            )
        except (CliInputError, ValueError) as exc:
            return _failed('security_contract_artifact_failed', exc)
        print(f'security_contract_artifact_ok:{artifact_path}')
        return 0

    if args.command == 'hash-artifact':
        artifact_path = Path(str(args.artifact))
        try:
            value = _load_json_value(artifact_path)
            if args.schema:
                validate_artifact(value, str(args.schema), allow_external_schema_refs=True)
            descriptor = build_artifact_hash(value)
        except (CliInputError, ValueError) as exc:
            return _failed('artifact_hash_failed', exc)
        if args.format == 'digest':
            print(descriptor['digest'])
        else:
            print(json.dumps(descriptor, indent=2, sort_keys=True))
        return 0

    if args.command in {'validate-chain', 'verify-lifecycle'}:
        manifest_path = Path(str(args.manifest)).resolve()
        root = Path(str(args.root)).resolve() if args.root else manifest_path.parent
        require_lifecycle = args.command == 'verify-lifecycle' or bool(getattr(args, 'strict_lifecycle', False))
        try:
            manifest = _load_json_object(manifest_path)
            result = verify_artifact_chain_manifest(
                manifest,
                root=root,
                validate_schemas=not args.no_schema,
                strict_jsonschema=bool(args.strict_jsonschema),
                require_lifecycle=require_lifecycle,
            )
            guard_result = None
            if _require_guard_requested(args):
                guard_result = _verify_required_guard_for_manifest(
                    args,
                    manifest_path,
                    require_lifecycle=require_lifecycle,
                )
        except ChainVerificationError as exc:
            print(f'artifact_chain_failed:{exc}', file=sys.stderr)
            return 1
        except CliInputError as exc:
            print(f'artifact_chain_failed:{exc}', file=sys.stderr)
            return 1
        except SecureBundleError as exc:
            print(f'kernel_guard_failed:{exc}', file=sys.stderr)
            return 1
        if guard_result is not None:
            result = {**result, 'guard_profile': guard_result['guard_profile'], 'guard_root_tag': guard_result['guard_root_tag'], 'key_id': guard_result['key_id'], 'security_posture': 'guarded_domain_auth'}
        if args.format == 'json':
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            label = 'lifecycle_ok' if args.command == 'verify-lifecycle' else 'artifact_chain_ok'
            suffix = f":guarded:{result['guard_root_tag']}" if guard_result is not None else ''
            print(f"{label}:{result['entry_count']}:{result['root_chain_digest']}{suffix}")
        return 0

    if args.command == 'verify-guarded-chain':
        manifest_path = Path(str(args.manifest)).resolve()
        guard_path = Path(str(args.guard)).resolve()
        root = Path(str(args.root)).resolve() if args.root else manifest_path.parent
        key = os.environ.get(str(args.guard_key_env) or '')
        if not key:
            print(f'kernel_guard_failed:missing guard key env {args.guard_key_env}', file=sys.stderr)
            return 1
        try:
            manifest = _load_json_object(manifest_path)
            guard = _load_json_object(guard_path)
            result = verify_kernel_guard_manifest(
                manifest,
                guard,
                key=key,
                root=root,
                validate_schemas=not args.no_schema,
                strict_jsonschema=bool(args.strict_jsonschema),
                require_lifecycle=bool(args.strict_lifecycle),
            )
        except KernelGuardError as exc:
            print(f'kernel_guard_failed:{exc}', file=sys.stderr)
            return 1
        except CliInputError as exc:
            print(f'kernel_guard_failed:{exc}', file=sys.stderr)
            return 1
        if args.format == 'json':
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"kernel_guard_ok:{result['entry_count']}:{result['root_chain_digest']}:{result['guard_root_tag']}")
        return 0

    if args.command == 'verify-secure-bundle':
        key = os.environ.get(str(args.guard_key_env) or '')
        if not key:
            print(f'secure_bundle_failed:missing guard key env {args.guard_key_env}', file=sys.stderr)
            return 1
        try:
            result = verify_secure_bundle(
                Path(str(args.target)),
                guard_path=args.guard,
                key=key,
                root=Path(str(args.root)).resolve() if args.root else None,
                validate_schemas=not args.no_schema,
                strict_jsonschema=bool(args.strict_jsonschema),
            )
        except SecureBundleError as exc:
            print(f'secure_bundle_failed:{exc}', file=sys.stderr)
            return 1
        if args.format == 'json':
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"secure_bundle_ok:{result['entry_count']}:{result['root_chain_digest']}:{result['guard_root_tag']}:replay_not_checked")
        return 0

    if args.command == 'validate-ticket':
        ticket_path = Path(str(args.ticket)).resolve()
        try:
            ticket = _load_json_object(ticket_path)
            if args.contract:
                contract = _load_json_object(Path(str(args.contract)).resolve())
                checks = validate_ticket_semantics(ticket, contract, strict_jsonschema=bool(args.strict_jsonschema))
            else:
                validate_ticket_schema(ticket, strict_jsonschema=bool(args.strict_jsonschema))
                checks = ['ticket_schema']
        except (TicketSemanticError, AssertionError, CliInputError) as exc:
            print(f'execution_ticket_failed:{exc}', file=sys.stderr)
            return 1
        if args.format == 'json':
            print(json.dumps({'status': 'passed', 'checks': checks, 'summary': ticket_summary(ticket)}, indent=2, sort_keys=True))
        else:
            print(f"execution_ticket_ok:{ticket.get('schema_version') or 'unknown'}:{ticket.get('ticket_profile') or 'unknown'}:{len(checks)}")
        return 0

    if args.command == 'explain-ticket':
        try:
            ticket = _load_json_object(Path(str(args.ticket)).resolve())
        except CliInputError as exc:
            return _failed('execution_ticket_failed', exc)
        print(explain_ticket(ticket))
        return 0

    if args.command == 'verify-ticket-use':
        try:
            ticket = _load_json_object(Path(str(args.ticket)).resolve())
            contract = _load_json_object(Path(str(args.contract)).resolve())
            receipt = _load_json_object(Path(str(args.receipt)).resolve())
            evidence = _load_json_object(Path(str(args.evidence_contract)).resolve()) if args.evidence_contract else None
            result = verify_ticket_use(
                ticket,
                contract,
                receipt,
                evidence,
                strict_jsonschema=bool(args.strict_jsonschema),
            )
        except (TicketSemanticError, TicketUseVerificationError, AssertionError, CliInputError) as exc:
            print(f'ticket_use_failed:{exc}', file=sys.stderr)
            return 1
        if args.format == 'json':
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"ticket_use_ok:{result['ticket_id']}:{result['receipt_id']}:{len(result['checks'])}")
        return 0

    if args.command in {'validate-trust-profile', 'validate-carrier-profile'}:
        profile_ref_path = Path(str(args.profile_ref)).resolve()
        subject_path = Path(str(args.subject)).resolve()
        try:
            profile_ref = _load_json_object(profile_ref_path)
            subject = _load_json_object(subject_path)
            if args.command == 'validate-trust-profile':
                checks = validate_trust_profile_ref(profile_ref, subject, strict_jsonschema=bool(args.strict_jsonschema))
                label = 'trust_profile_ref_ok'
            else:
                checks = validate_carrier_profile_ref(profile_ref, subject, strict_jsonschema=bool(args.strict_jsonschema))
                label = 'carrier_profile_ref_ok'
        except (ProfileReferenceError, AssertionError, CliInputError) as exc:
            print(f'profile_ref_failed:{exc}', file=sys.stderr)
            return 1
        summary = profile_ref_summary(profile_ref)
        if args.format == 'json':
            print(json.dumps({'status': 'passed', 'checks': checks, 'summary': summary}, indent=2, sort_keys=True))
        else:
            print(f"{label}:{summary['profile']}:{summary['subject_artifact_digest']}:{len(checks)}")
        return 0

    if args.command == 'redaction-policy':
        policy = build_default_redaction_policy(policy_id=str(args.policy_id))
        print(json.dumps(policy, indent=2, sort_keys=True))
        return 0

    if args.command == 'redaction-receipt':
        try:
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
        except (CliInputError, ValueError) as exc:
            return _failed('redaction_receipt_failed', exc)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0

    if args.command == 'validation-surface-index':
        index = build_public_validation_surface_index(generated_at=args.generated_at)
        print(json.dumps(index, indent=2, sort_keys=True))
        return 0

    if args.command == 'snapshot-manifest':
        files = []
        try:
            for item in args.file:
                path = Path(str(item))
                value = _load_json_value(path)
                artifact_type = value.get('artifact_type') if isinstance(value, dict) else ''
                files.append({'path': str(path), 'artifact_type': str(artifact_type or ''), 'schema': '', 'public_safe': True, 'value': value})
            manifest = build_public_snapshot_manifest(files, snapshot_name=str(args.snapshot_name), snapshot_version=str(args.snapshot_version))
        except (CliInputError, ValueError) as exc:
            return _failed('snapshot_manifest_failed', exc)
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0

    if args.command == 'scope-fidelity':
        if args.approved_spec:
            approved_path = Path(str(args.approved_spec))
            try:
                spec = _load_json_object(approved_path)
                report = build_scope_fidelity_report_from_approved_spec(spec, source_artifact=args.source_artifact or str(approved_path))
            except (CliInputError, ValueError) as exc:
                return _failed('scope_fidelity_failed', exc)
        else:
            if not args.target:
                print('scope-fidelity requires --approved-spec or --target', file=sys.stderr)
                return 2
            plan = []
            for item in args.plan_step_json:
                try:
                    value = _parse_json_object(str(item), source='--plan-step-json')
                    plan.append(value)
                except CliInputError as exc:
                    return _failed('scope_fidelity_failed', exc)
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

    if args.command == 'review-lifecycle':
        manifest_path = Path(str(args.manifest)).resolve()
        if _require_guard_requested(args):
            try:
                _verify_required_guard_for_manifest(args, manifest_path, require_lifecycle=True)
            except (SecureBundleError, CliInputError) as exc:
                print(f'review_lifecycle_failed:{exc}', file=sys.stderr)
                return 1
        try:
            record = build_review_record_from_manifest(
                manifest_path,
                root=Path(str(args.root)).resolve() if args.root else None,
                strict_jsonschema=bool(args.strict_jsonschema),
            )
        except (ReviewRecordError, AssertionError, ValueError) as exc:
            print(f'review_lifecycle_failed:{exc}', file=sys.stderr)
            return 1
        if args.format == 'markdown':
            print(review_record_markdown(record), end='')
        else:
            print(json.dumps(record, indent=2, sort_keys=True))
        return _scope_fidelity_exit_code(str(record['verdict']), str(args.fail_on))

    if args.command == 'review':
        bundle_dir = Path(str(args.bundle_dir)).resolve()
        if _require_guard_requested(args):
            try:
                verify_secure_bundle(
                    bundle_dir,
                    guard_path=args.guard,
                    key=_guard_key_from_env(str(args.guard_key_env)),
                    validate_schemas=True,
                    strict_jsonschema=bool(args.strict_jsonschema),
                )
            except SecureBundleError as exc:
                print(f'review_bundle_failed:{exc}', file=sys.stderr)
                return 1
        try:
            record = review_bundle(
                bundle_dir,
                strict_jsonschema=bool(args.strict_jsonschema),
            )
        except (ReviewBundleError, AssertionError, ValueError) as exc:
            print(f'review_bundle_failed:{exc}', file=sys.stderr)
            return 1
        if args.format == 'markdown':
            print(export_review_bundle_markdown(record), end='')
        elif args.format == 'summary':
            print(review_bundle_summary(record))
        else:
            print(json.dumps(record, indent=2, sort_keys=True))
        return _scope_fidelity_exit_code(str(record['verdict']), str(args.fail_on))

    if args.command == 'export-review-bundle':
        try:
            record = review_bundle(
                Path(str(args.bundle_dir)),
                strict_jsonschema=bool(args.strict_jsonschema),
            )
        except (ReviewBundleError, AssertionError, ValueError) as exc:
            print(f'export_review_bundle_failed:{exc}', file=sys.stderr)
            return 1
        payload = json.dumps(record, indent=2, sort_keys=True) + '\n' if args.format == 'json' else export_review_bundle_markdown(record)
        if args.output:
            Path(str(args.output)).write_text(payload, encoding='utf-8')
        else:
            print(payload, end='')
        return 0

    parser.error('unknown command')
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
