from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping

from .redaction import sanitize_public_artifact


POLICY_DECISION_SCHEMA_VERSION = '2026-04-27.policy-decision.v0.1'
PREPARED_EXECUTION_SPEC_VERSION = '2026-03-18.prepared.v1'
PREPARED_EXECUTION_SPEC_ARTIFACT_TYPE = 'prepared_execution_spec'
REDACTED_PREPARED_EXECUTION_SPEC_ARTIFACT_TYPE = 'redacted_prepared_execution_spec'
APPROVED_EXECUTION_SPEC_VERSION = '2026-03-18.approved.v1'
EXECUTION_RECEIPT_ARTIFACT_TYPE = 'execution_receipt'
EVIDENCE_BUNDLE_SCHEMA_VERSION = '2026-04-28.evidence-bundle.v0.1'
EVIDENCE_BUNDLE_ARTIFACT_TYPE = 'evidence_bundle'
DEMO_PROOF_MODE = 'dry_run_contract_proof'
PUBLIC_DEMO_TARGET_HOST = 'example.com'
ARTIFACT_CANONICALIZATION_VERSION = 'sclite-json-v0.1'
ARTIFACT_HASH_ALGORITHM = 'sha256'

POLICY_DECISION_FILE = 'policy_decision.json'
REDACTED_PREPARED_EXECUTION_SPEC_FILE = 'prepared_execution_spec.redacted.json'
APPROVED_EXECUTION_SPEC_FILE = 'approved_execution_spec.json'
EXECUTION_RECEIPT_FILE = 'execution_receipt.json'
EVIDENCE_BUNDLE_FILE = 'evidence_bundle.json'
EVIDENCE_SUMMARY_FILE = 'evidence_summary.md'

PUBLIC_DEMO_NON_CLAIMS = [
    'does_not_claim_live_vulnerability_evidence',
    'does_not_execute_against_live_private_targets',
    'does_not_include_raw_stdout_stderr_or_private_paths',
]

PROOF_TRACE_FILES = [
    POLICY_DECISION_FILE,
    REDACTED_PREPARED_EXECUTION_SPEC_FILE,
    APPROVED_EXECUTION_SPEC_FILE,
    EXECUTION_RECEIPT_FILE,
    EVIDENCE_BUNDLE_FILE,
    EVIDENCE_SUMMARY_FILE,
]

SCHEMA_FILES = {
    'policy_decision.v0.1': 'policy_decision.v0.1.schema.json',
    'prepared_execution_spec.v0.1': 'prepared_execution_spec.v0.1.schema.json',
    'redacted_prepared_execution_spec.v0.1': 'redacted_prepared_execution_spec.v0.1.schema.json',
    'approved_execution_spec.v0.1': 'approved_execution_spec.v0.1.schema.json',
    'execution_receipt.v0.1': 'execution_receipt.v0.1.schema.json',
    'evidence_bundle.v0.1': 'evidence_bundle.v0.1.schema.json',
    'scope_fidelity_report.v0.1': 'scope_fidelity_report.v0.1.schema.json',
    'security_contract_validation_receipt.v0.1': 'security_contract_validation_receipt.v0.1.schema.json',
    'redaction_policy.v0.1': 'redaction_policy.v0.1.schema.json',
    'redaction_receipt.v0.1': 'redaction_receipt.v0.1.schema.json',
    'public_validation_surface_index.v0.1': 'public_validation_surface_index.v0.1.schema.json',
    'public_snapshot_manifest.v0.1': 'public_snapshot_manifest.v0.1.schema.json',
    'intent_contract.v0.2': 'intent_contract.v0.2.schema.json',
    'policy_decision.v0.2': 'policy_decision.v0.2.schema.json',
    'execution_contract.v0.2': 'execution_contract.v0.2.schema.json',
    'execution_ticket.v0.2': 'execution_ticket.v0.2.schema.json',
    'execution_ticket.v0.3': 'execution_ticket.v0.3.schema.json',
    'execution_receipt.v0.2': 'execution_receipt.v0.2.schema.json',
    'evidence_contract.v0.2': 'evidence_contract.v0.2.schema.json',
    'artifact_chain_manifest.v0.2': 'artifact_chain_manifest.v0.2.schema.json',
    'trust_profile_ref.v0.1': 'trust_profile_ref.v0.1.schema.json',
    'carrier_profile_ref.v0.1': 'carrier_profile_ref.v0.1.schema.json',
}


class ProofTraceInvariantError(ValueError):
    pass


class JsonSchemaValidationError(AssertionError):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def package_root() -> Path:
    return Path(__file__).resolve().parent


def schema_dir() -> Path:
    return package_root() / 'schemas'


def examples_dir() -> Path:
    return package_root() / 'examples'


def _json_type_name(value: Any) -> str:
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, dict):
        return 'object'
    if isinstance(value, list):
        return 'array'
    if isinstance(value, int) and not isinstance(value, bool):
        return 'integer'
    if isinstance(value, float):
        return 'number'
    if isinstance(value, str):
        return 'string'
    if value is None:
        return 'null'
    return type(value).__name__


def _assert_json_schema_type(value: Any, expected: Any, path: str) -> None:
    expected_types = expected if isinstance(expected, list) else [expected]
    actual = _json_type_name(value)
    if actual == 'integer' and 'number' in expected_types:
        return
    if actual not in expected_types:
        raise JsonSchemaValidationError(f'{path}: expected {expected_types}, got {actual}')


def validate_json_schema_value(schema: Mapping[str, Any], value: Any, path: str = '$') -> None:
    """Validate the JSON Schema subset used by SCL v0.1 artifacts."""
    if 'const' in schema and value != schema['const']:
        raise JsonSchemaValidationError(f'{path}: expected const {schema["const"]!r}, got {value!r}')
    if 'enum' in schema and value not in schema['enum']:
        raise JsonSchemaValidationError(f'{path}: expected one of {schema["enum"]!r}, got {value!r}')
    if 'type' in schema:
        _assert_json_schema_type(value, schema['type'], path)
    if isinstance(value, str) and 'minLength' in schema and len(value) < int(schema['minLength']):
        raise JsonSchemaValidationError(f'{path}: expected minLength {schema["minLength"]}')
    if isinstance(value, (int, float)) and not isinstance(value, bool) and 'minimum' in schema and value < float(schema['minimum']):
        raise JsonSchemaValidationError(f'{path}: expected minimum {schema["minimum"]}')
    if schema.get('type') == 'object':
        if not isinstance(value, dict):
            raise JsonSchemaValidationError(f'{path}: expected object')
        for key in schema.get('required', []):
            if key not in value:
                raise JsonSchemaValidationError(f'{path}: missing required field {key!r}')
        properties = schema.get('properties') if isinstance(schema.get('properties'), dict) else {}
        for key, subschema in properties.items():
            if key in value and isinstance(subschema, dict):
                validate_json_schema_value(subschema, value[key], f'{path}.{key}')
        if schema.get('additionalProperties') is False:
            extra = sorted(set(value) - set(properties))
            if extra:
                raise JsonSchemaValidationError(f'{path}: unexpected fields {extra!r}')
    if schema.get('type') == 'array':
        if not isinstance(value, list):
            raise JsonSchemaValidationError(f'{path}: expected array')
        item_schema = schema.get('items')
        if isinstance(item_schema, dict):
            for idx, item in enumerate(value):
                validate_json_schema_value(item_schema, item, f'{path}[{idx}]')


def _resolve_schema_ref(schema_ref: str, *, root: Path | None = None) -> Path:
    raw_ref = str(schema_ref or '')
    candidates: List[Path] = []
    if root is not None:
        candidates.append(root / raw_ref)
    candidates.append(repo_root() / raw_ref)
    basename = Path(raw_ref).name
    if raw_ref in SCHEMA_FILES:
        basename = SCHEMA_FILES[raw_ref]
    candidates.append(schema_dir() / basename)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def load_json_schema(schema_ref: str, *, root: Path | None = None) -> Dict[str, Any]:
    schema_path = _resolve_schema_ref(schema_ref, root=root)
    value = json.loads(schema_path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise JsonSchemaValidationError(f'{schema_ref}: schema root is not an object')
    return value


def validate_schema_ref(
    schema_ref: str,
    value: Any,
    *,
    root: Path | None = None,
    path: str = '$',
    strict_jsonschema: bool = False,
) -> None:
    schema = load_json_schema(schema_ref, root=root)
    if strict_jsonschema:
        try:
            import jsonschema
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise JsonSchemaValidationError(
                "strict JSON Schema validation requires the optional 'jsonschema' dependency; "
                "install with: pip install 'sclite-core[jsonschema]'"
            ) from exc
        try:
            jsonschema.Draft202012Validator(schema).validate(value)
        except jsonschema.ValidationError as exc:
            location = '.'.join(str(part) for part in exc.absolute_path) or path
            raise JsonSchemaValidationError(f'{location}: {exc.message}') from exc
        return
    validate_json_schema_value(schema, value, path=path)


def validate_artifact(value: Any, schema_name: str, *, root: Path | None = None, strict_jsonschema: bool = False) -> None:
    """Validate one artifact against a named SCL schema.

    By default this uses SCLite's dependency-free schema subset validator.
    Pass strict_jsonschema=True to use Draft 2020-12 validation via the
    optional jsonschema extra.
    """
    validate_schema_ref(schema_name, value, root=root, strict_jsonschema=strict_jsonschema)


def canonicalize_artifact(value: Any) -> str:
    """Return deterministic compact JSON for a JSON-compatible artifact.

    The v0.1 canonicalization is intentionally small: UTF-8 JSON with sorted
    object keys, compact separators, preserved Unicode, and no NaN/Infinity.
    It is a content-addressing helper, not a signature or tamper-proof proof.
    """
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def canonical_artifact_bytes(value: Any) -> bytes:
    """Return UTF-8 bytes for the v0.1 canonical JSON representation."""
    return canonicalize_artifact(value).encode('utf-8')


def artifact_sha256(value: Any) -> str:
    """Return SHA-256 hex digest over v0.1 canonical artifact bytes."""
    return hashlib.sha256(canonical_artifact_bytes(value)).hexdigest()


def build_artifact_hash(value: Any) -> Dict[str, Any]:
    """Return a public-safe hash descriptor for one JSON-compatible artifact."""
    canonical = canonical_artifact_bytes(value)
    return {
        'canonicalization': ARTIFACT_CANONICALIZATION_VERSION,
        'algorithm': ARTIFACT_HASH_ALGORITHM,
        'digest': hashlib.sha256(canonical).hexdigest(),
        'canonical_bytes': len(canonical),
    }


def build_execution_receipt_artifact(pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
    engine = dict(pipeline_data.get('engine') or {}) if isinstance(pipeline_data.get('engine'), dict) else {}
    return sanitize_public_artifact({
        'artifact_type': EXECUTION_RECEIPT_ARTIFACT_TYPE,
        'runtime_mode': str((pipeline_data.get('settings') or {}).get('runtime_mode') or ''),
        'status': str(engine.get('status') or ''),
        'returncode': int(engine.get('returncode', 0) or 0),
        'reason': str(engine.get('reason') or ''),
        'execution_source': str(engine.get('execution_source') or ''),
        'dry_run': str(engine.get('status') or '') == 'dry-run',
        'compiled_action': dict(engine.get('compiled_action') or {}) if isinstance(engine.get('compiled_action'), dict) else {},
        'command_input_summary': dict(engine.get('command_input_summary') or {}) if isinstance(engine.get('command_input_summary'), dict) else {},
        'planned_command_count': len(engine.get('planned_commands') or []) if isinstance(engine.get('planned_commands'), list) else 0,
        'executed_command_count': len(engine.get('executed_commands') or []) if isinstance(engine.get('executed_commands'), list) else 0,
        'stdout_present': bool(engine.get('stdout')),
        'stderr_present': bool(engine.get('stderr')),
    })


def build_demo_success_criteria(pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
    """Return public-safe proof criteria for a dry-run SCL proof bundle."""
    existing = pipeline_data.get('success_criteria')
    if isinstance(existing, dict) and isinstance(existing.get('evidence'), list) and existing.get('evidence'):
        return sanitize_public_artifact(existing)

    runtime_mode = str((pipeline_data.get('settings') or {}).get('runtime_mode') or '')
    engine = dict(pipeline_data.get('engine') or {}) if isinstance(pipeline_data.get('engine'), dict) else {}
    policy_gate = dict(pipeline_data.get('policy_gate') or {}) if isinstance(pipeline_data.get('policy_gate'), dict) else {}
    approved = pipeline_data.get('approved_execution_spec') if isinstance(pipeline_data.get('approved_execution_spec'), dict) else {}
    prepared = pipeline_data.get('prepared_execution_spec') if isinstance(pipeline_data.get('prepared_execution_spec'), dict) else {}

    criteria = [
        {
            'id': 'demo_runtime_mode',
            'claim': 'Demo bundle was generated in demo mode.',
            'source': 'run_pipeline.demo.json',
            'status': 'met' if runtime_mode == 'demo' else 'not_met',
            'observed': runtime_mode,
        },
        {
            'id': 'policy_decision_recorded',
            'claim': 'Policy gate decision was captured as a contract artifact.',
            'source': POLICY_DECISION_FILE,
            'status': 'met' if policy_gate else 'not_met',
            'observed': str(policy_gate.get('reason') or ''),
        },
        {
            'id': 'prepared_spec_redacted',
            'claim': 'Prepared execution spec can be redacted for public/auditor review.',
            'source': REDACTED_PREPARED_EXECUTION_SPEC_FILE,
            'status': 'met' if prepared else 'not_met',
        },
        {
            'id': 'approved_spec_recorded',
            'claim': 'Approved execution spec was produced before executor handoff.',
            'source': APPROVED_EXECUTION_SPEC_FILE,
            'status': 'met' if approved else 'not_met',
            'observed': str((approved or {}).get('spec_version') or ''),
        },
        {
            'id': 'dry_run_receipt_recorded',
            'claim': 'Execution receipt records dry-run/mock execution instead of live offensive execution.',
            'source': EXECUTION_RECEIPT_FILE,
            'status': 'met' if str(engine.get('status') or '') == 'dry-run' else 'not_met',
            'observed': str(engine.get('status') or ''),
        },
        {
            'id': 'public_safe_target',
            'claim': 'Public demo target remains example.com/local-safe.',
            'source': APPROVED_EXECUTION_SPEC_FILE,
            'status': 'met' if str((approved or {}).get('target_host') or '') == PUBLIC_DEMO_TARGET_HOST else 'not_met',
            'observed': str((approved or {}).get('target_host') or ''),
        },
    ]
    met = all(item.get('status') == 'met' for item in criteria)
    return sanitize_public_artifact({
        'status': DEMO_PROOF_MODE,
        'met': met,
        'gap': 'live_target_evidence_not_collected_by_design',
        'evidence': criteria,
        'non_claims': list(PUBLIC_DEMO_NON_CLAIMS),
    })


def build_evidence_bundle_artifact(pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
    success = build_demo_success_criteria(pipeline_data)
    evidence = success.get('evidence') if isinstance(success.get('evidence'), list) else []
    settings = dict(pipeline_data.get('settings') or {}) if isinstance(pipeline_data.get('settings'), dict) else {}
    approved = dict(pipeline_data.get('approved_execution_spec') or {}) if isinstance(pipeline_data.get('approved_execution_spec'), dict) else {}
    engine = dict(pipeline_data.get('engine') or {}) if isinstance(pipeline_data.get('engine'), dict) else {}
    runtime_mode = str(settings.get('runtime_mode') or '')
    target_host = str(approved.get('target_host') or '')
    dry_run = str(engine.get('status') or '') == 'dry-run'
    return sanitize_public_artifact({
        'schema_version': EVIDENCE_BUNDLE_SCHEMA_VERSION,
        'artifact_type': EVIDENCE_BUNDLE_ARTIFACT_TYPE,
        'proof_mode': DEMO_PROOF_MODE,
        'status': str(success.get('status') or ''),
        'met': bool(success.get('met', False)),
        'gap': str(success.get('gap') or ''),
        'evidence_items': len(evidence),
        'criteria': evidence,
        'non_claims': list(success.get('non_claims') or []) if isinstance(success.get('non_claims'), list) else [],
        'source_artifacts': {
            'policy_decision': POLICY_DECISION_FILE,
            'prepared_execution_spec': REDACTED_PREPARED_EXECUTION_SPEC_FILE,
            'approved_execution_spec': APPROVED_EXECUTION_SPEC_FILE,
            'execution_receipt': EXECUTION_RECEIPT_FILE,
            'evidence_summary': EVIDENCE_SUMMARY_FILE,
        },
        'public_safety': {
            'runtime_mode': runtime_mode,
            'target_host': target_host,
            'dry_run': dry_run,
            'raw_live_evidence_included': False,
            'raw_stdout_stderr_included': False,
        },
    })


def build_evidence_summary_markdown(pipeline_data: Dict[str, Any]) -> str:
    bundle = build_evidence_bundle_artifact(pipeline_data)
    evidence = bundle.get('criteria') if isinstance(bundle.get('criteria'), list) else []
    lines = [
        '# Ravenclaw Demo Evidence Summary',
        '',
        f"- final_status: `{pipeline_data.get('final_status', '')}`",
        f"- reason_code: `{pipeline_data.get('reason_code', '')}`",
        f"- success_status: `{bundle.get('status', 'not_provided')}`",
        f"- success_met: `{bool(bundle.get('met', False))}`",
        f"- evidence_items: `{len(evidence)}`",
        '',
        '## Evidence criteria',
        '',
    ]
    gap = str(bundle.get('gap') or '').strip()
    if gap:
        lines.insert(6, f"- evidence_gap: `{gap}`")
    for item in evidence:
        if not isinstance(item, dict):
            continue
        observed = str(item.get('observed') or '').strip()
        suffix = f" Observed: `{observed}`." if observed else ''
        lines.append(f"- `{item.get('status', '')}` — {item.get('id', '')}: {item.get('claim', '')} Source: `{item.get('source', '')}`.{suffix}")
    non_claims = bundle.get('non_claims') if isinstance(bundle.get('non_claims'), list) else []
    if non_claims:
        lines.extend(['', '## Non-claims', ''])
        for item in non_claims:
            lines.append(f"- `{item}`")
    lines.extend([
        '',
        'This public demo bundle is dry-run/local and intentionally does not include raw live-target evidence.',
    ])
    return '\n'.join(lines) + '\n'


def build_proof_trace_artifacts(
    pipeline_data: Dict[str, Any],
    *,
    policy_decision_artifact: Dict[str, Any] | None = None,
    redacted_prepared_execution_spec: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build public-safe proof trace artifacts from already-prepared inputs.

    Ravenclaw-specific adapters supply the policy decision and richer prepared
    spec redaction. SCL then owns the artifact ordering and public-safety checks.
    """
    approved = dict(pipeline_data.get('approved_execution_spec') or {}) if isinstance(pipeline_data.get('approved_execution_spec'), dict) else {}
    return {
        POLICY_DECISION_FILE: sanitize_public_artifact(policy_decision_artifact or {}),
        REDACTED_PREPARED_EXECUTION_SPEC_FILE: sanitize_public_artifact(redacted_prepared_execution_spec or {}),
        APPROVED_EXECUTION_SPEC_FILE: sanitize_public_artifact(approved),
        EXECUTION_RECEIPT_FILE: build_execution_receipt_artifact(pipeline_data),
        EVIDENCE_BUNDLE_FILE: build_evidence_bundle_artifact(pipeline_data),
        EVIDENCE_SUMMARY_FILE: build_evidence_summary_markdown(pipeline_data),
    }


def proof_trace_manifest() -> Dict[str, Dict[str, str]]:
    return {
        POLICY_DECISION_FILE: {
            'kind': 'json',
            'schema': 'schemas/policy_decision.v0.1.schema.json',
            'schema_version': POLICY_DECISION_SCHEMA_VERSION,
        },
        REDACTED_PREPARED_EXECUTION_SPEC_FILE: {
            'kind': 'json',
            'schema': 'schemas/redacted_prepared_execution_spec.v0.1.schema.json',
            'schema_version': PREPARED_EXECUTION_SPEC_VERSION,
        },
        APPROVED_EXECUTION_SPEC_FILE: {
            'kind': 'json',
            'schema': 'schemas/approved_execution_spec.v0.1.schema.json',
            'schema_version': APPROVED_EXECUTION_SPEC_VERSION,
        },
        EXECUTION_RECEIPT_FILE: {
            'kind': 'json',
            'schema': 'schemas/execution_receipt.v0.1.schema.json',
            'artifact_type': EXECUTION_RECEIPT_ARTIFACT_TYPE,
        },
        EVIDENCE_BUNDLE_FILE: {
            'kind': 'json',
            'schema': 'schemas/evidence_bundle.v0.1.schema.json',
            'schema_version': EVIDENCE_BUNDLE_SCHEMA_VERSION,
        },
        EVIDENCE_SUMMARY_FILE: {
            'kind': 'markdown',
            'schema': '',
            'schema_version': '',
        },
    }


def _expect_dict(artifacts: Dict[str, Any], filename: str, errors: List[str]) -> Dict[str, Any]:
    value = artifacts.get(filename)
    if not isinstance(value, dict):
        errors.append(f'{filename}:not_object')
        return {}
    return value


def validate_public_proof_trace_artifacts(artifacts: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for filename in PROOF_TRACE_FILES:
        if filename not in artifacts:
            errors.append(f'{filename}:missing')

    policy = _expect_dict(artifacts, POLICY_DECISION_FILE, errors)
    if policy:
        if policy.get('schema_version') != POLICY_DECISION_SCHEMA_VERSION:
            errors.append(f'{POLICY_DECISION_FILE}:schema_version')
        if policy.get('decision') not in {'allow_prepare', 'owner_approval_required', 'deny'}:
            errors.append(f'{POLICY_DECISION_FILE}:decision')
        if policy.get('redaction_required') is not True:
            errors.append(f'{POLICY_DECISION_FILE}:redaction_required')

    prepared = _expect_dict(artifacts, REDACTED_PREPARED_EXECUTION_SPEC_FILE, errors)
    if prepared:
        if prepared.get('artifact_type') != REDACTED_PREPARED_EXECUTION_SPEC_ARTIFACT_TYPE:
            errors.append(f'{REDACTED_PREPARED_EXECUTION_SPEC_FILE}:artifact_type')
        if prepared.get('spec_version') != PREPARED_EXECUTION_SPEC_VERSION:
            errors.append(f'{REDACTED_PREPARED_EXECUTION_SPEC_FILE}:spec_version')
        redaction = prepared.get('redaction') if isinstance(prepared.get('redaction'), dict) else {}
        safety = prepared.get('public_safety') if isinstance(prepared.get('public_safety'), dict) else {}
        if redaction.get('raw_stdout_stderr_included') is not False:
            errors.append(f'{REDACTED_PREPARED_EXECUTION_SPEC_FILE}:raw_stdout_stderr_redaction')
        if redaction.get('credentials_included') is not False:
            errors.append(f'{REDACTED_PREPARED_EXECUTION_SPEC_FILE}:credentials_redaction')
        if redaction.get('private_paths_included') is not False:
            errors.append(f'{REDACTED_PREPARED_EXECUTION_SPEC_FILE}:private_paths_redaction')
        if safety.get('live_target_execution') is not False:
            errors.append(f'{REDACTED_PREPARED_EXECUTION_SPEC_FILE}:live_target_execution')
        if safety.get('raw_live_evidence_included') is not False:
            errors.append(f'{REDACTED_PREPARED_EXECUTION_SPEC_FILE}:raw_live_evidence')
        if safety.get('raw_stdout_stderr_included') is not False:
            errors.append(f'{REDACTED_PREPARED_EXECUTION_SPEC_FILE}:raw_stdout_stderr')
        if any(secret in str(prepared) for secret in ('private-researcher-handle', 'session=abc', str(repo_root()))):
            errors.append(f'{REDACTED_PREPARED_EXECUTION_SPEC_FILE}:public_sanitization')

    approved = _expect_dict(artifacts, APPROVED_EXECUTION_SPEC_FILE, errors)
    if approved:
        if approved.get('spec_version') != APPROVED_EXECUTION_SPEC_VERSION:
            errors.append(f'{APPROVED_EXECUTION_SPEC_FILE}:spec_version')
        if str(approved.get('target_host') or '') != PUBLIC_DEMO_TARGET_HOST:
            errors.append(f'{APPROVED_EXECUTION_SPEC_FILE}:public_target')

    receipt = _expect_dict(artifacts, EXECUTION_RECEIPT_FILE, errors)
    if receipt:
        if receipt.get('artifact_type') != EXECUTION_RECEIPT_ARTIFACT_TYPE:
            errors.append(f'{EXECUTION_RECEIPT_FILE}:artifact_type')
        if receipt.get('dry_run') is not True:
            errors.append(f'{EXECUTION_RECEIPT_FILE}:dry_run')
        if 'stdout' in receipt or 'stderr' in receipt:
            errors.append(f'{EXECUTION_RECEIPT_FILE}:raw_output_present')

    bundle = _expect_dict(artifacts, EVIDENCE_BUNDLE_FILE, errors)
    if bundle:
        if bundle.get('schema_version') != EVIDENCE_BUNDLE_SCHEMA_VERSION:
            errors.append(f'{EVIDENCE_BUNDLE_FILE}:schema_version')
        if bundle.get('artifact_type') != EVIDENCE_BUNDLE_ARTIFACT_TYPE:
            errors.append(f'{EVIDENCE_BUNDLE_FILE}:artifact_type')
        if bundle.get('proof_mode') != DEMO_PROOF_MODE:
            errors.append(f'{EVIDENCE_BUNDLE_FILE}:proof_mode')
        criteria = bundle.get('criteria') if isinstance(bundle.get('criteria'), list) else []
        evidence_items = bundle.get('evidence_items')
        if not isinstance(evidence_items, int) or evidence_items != len(criteria):
            errors.append(f'{EVIDENCE_BUNDLE_FILE}:evidence_items_mismatch')
        safety = bundle.get('public_safety') if isinstance(bundle.get('public_safety'), dict) else {}
        if safety.get('runtime_mode') != 'demo':
            errors.append(f'{EVIDENCE_BUNDLE_FILE}:runtime_mode')
        if safety.get('target_host') != PUBLIC_DEMO_TARGET_HOST:
            errors.append(f'{EVIDENCE_BUNDLE_FILE}:target_host')
        if safety.get('dry_run') is not True:
            errors.append(f'{EVIDENCE_BUNDLE_FILE}:dry_run')
        if safety.get('raw_live_evidence_included') is not False:
            errors.append(f'{EVIDENCE_BUNDLE_FILE}:raw_live_evidence')
        if safety.get('raw_stdout_stderr_included') is not False:
            errors.append(f'{EVIDENCE_BUNDLE_FILE}:raw_stdout_stderr')
        non_claims = set(str(item) for item in (bundle.get('non_claims') or []))
        for item in PUBLIC_DEMO_NON_CLAIMS:
            if item not in non_claims:
                errors.append(f'{EVIDENCE_BUNDLE_FILE}:missing_non_claim:{item}')

    summary = artifacts.get(EVIDENCE_SUMMARY_FILE)
    if not isinstance(summary, str):
        errors.append(f'{EVIDENCE_SUMMARY_FILE}:not_markdown')
    elif 'does_not_claim_live_vulnerability_evidence' not in summary:
        errors.append(f'{EVIDENCE_SUMMARY_FILE}:missing_non_claims')
    return errors


def assert_public_proof_trace_artifacts(artifacts: Dict[str, Any]) -> None:
    errors = validate_public_proof_trace_artifacts(artifacts)
    if errors:
        raise ProofTraceInvariantError(';'.join(errors))


def validate_trace(path: str | Path) -> List[str]:
    from .validation import validate_fixture_dir

    return validate_fixture_dir(Path(path))
