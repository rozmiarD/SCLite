from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping
import warnings

from .json_types import json_array
from .disclosure import build_disclosure_status


SENSITIVE_VALUE_KEYS = {
    'password',
    'password_ref',
    'secret',
    'token',
    'api_key',
    'apikey',
    'authorization',
    'auth',
    'cookie',
    'cookies',
}

PUBLIC_REDACTION_PLACEHOLDER = '<redacted>'
PATH_REDACTION_PLACEHOLDER = '<local_path_omitted>'
REDACTION_POLICY_ARTIFACT_TYPE = 'redaction_policy'
REDACTION_POLICY_SCHEMA_VERSION = 'v0.2'
REDACTION_RECEIPT_ARTIFACT_TYPE = 'redaction_receipt'
REDACTION_RECEIPT_SCHEMA_VERSION = 'v0.2'


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _sanitize_string(value: Any) -> str:
    text = str(value or '')
    root = str(_repo_root())
    if root and root in text:
        text = text.replace(root, PATH_REDACTION_PLACEHOLDER)
    if text.startswith('/home/'):
        return PATH_REDACTION_PLACEHOLDER
    lowered = text.lower()
    if ':' in text and any(marker in lowered for marker in ('authorization', 'cookie', 'token', 'secret', 'api-key', 'api_key')):
        name = text.split(':', 1)[0]
        return f'{name}: {PUBLIC_REDACTION_PLACEHOLDER}'
    if 'session=' in lowered:
        return PUBLIC_REDACTION_PLACEHOLDER
    return text


def sanitize_public_artifact(value: Any) -> Any:
    """Return a public-safe JSON-like value for SCL examples and receipts.

    This helper removes values that should not appear in public-safe fixtures. It
    is intentionally conservative and does not claim to be a complete secret
    scanner.
    """
    warnings.warn(
        'sanitize_public_artifact is a devtools compatibility helper, not publication authority',
        DeprecationWarning,
        stacklevel=2,
    )
    if isinstance(value, dict):
        if isinstance(value.get('name'), str) and ('value' in value or 'raw' in value):
            named_value = {k: sanitize_public_artifact(v) for k, v in value.items()}
            named_value['value'] = PUBLIC_REDACTION_PLACEHOLDER
            if 'raw' in named_value:
                named_value['raw'] = f"{value.get('name')}: {PUBLIC_REDACTION_PLACEHOLDER}"
            return named_value
        sanitized: Dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key or '').lower()
            if key_text in SENSITIVE_VALUE_KEYS and item:
                sanitized[key] = PUBLIC_REDACTION_PLACEHOLDER
            elif key_text in {'stdout', 'stderr'}:
                sanitized[key] = '' if not item else '<omitted_for_public_demo>'
            else:
                sanitized[key] = sanitize_public_artifact(item)
        return sanitized
    if isinstance(value, list):
        return [sanitize_public_artifact(item) for item in value]
    if isinstance(value, str):
        return _sanitize_string(value)
    return value


def redact_prepared_spec(value: Any) -> Any:
    """Return a generic public-safe redaction of a prepared spec-shaped value.

    Ravenclaw keeps its richer prepared-spec redactor in the runtime adapter.
    This generic helper is for SCL fixture and CLI safety checks only.
    """
    return sanitize_public_artifact(value)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_default_redaction_policy(*, policy_id: str = 'sclite-public-safe-v0.1') -> Dict[str, Any]:
    """Return SCLite's default public-safe redaction policy descriptor."""
    rules = [
        {
            'rule_id': 'sensitive_value_keys',
            'description': 'Redact values for common secret-bearing keys such as token, secret, authorization, cookie, and password.',
            'applies_to': sorted(SENSITIVE_VALUE_KEYS),
            'action': 'replace_value',
            'replacement': PUBLIC_REDACTION_PLACEHOLDER,
        },
        {
            'rule_id': 'raw_stdout_stderr',
            'description': 'Omit raw stdout/stderr content from public artifacts.',
            'applies_to': ['stdout', 'stderr'],
            'action': 'omit_or_replace',
            'replacement': '<omitted_for_public_demo>',
        },
        {
            'rule_id': 'local_paths',
            'description': 'Replace local home/workspace paths with a public-safe placeholder.',
            'applies_to': ['string_values'],
            'action': 'replace_local_path',
            'replacement': PATH_REDACTION_PLACEHOLDER,
        },
        {
            'rule_id': 'header_like_secrets',
            'description': 'Redact header-like strings containing authorization, cookie, token, secret, or api-key markers.',
            'applies_to': ['string_values'],
            'action': 'replace_header_value',
            'replacement': PUBLIC_REDACTION_PLACEHOLDER,
        },
    ]
    return {
        'artifact_type': REDACTION_POLICY_ARTIFACT_TYPE,
        'schema_version': REDACTION_POLICY_SCHEMA_VERSION,
        'policy_id': policy_id,
        'mode': 'public_safe_fixture_redaction',
        'rules': rules,
        'disclosure': build_disclosure_status(status='operator_asserted'),
        'public_safety': {
            'live_target_execution': False,
            'raw_live_evidence_included': False,
            'raw_stdout_stderr_included': False,
            'credentials_included': 'unknown',
            'private_paths_included': 'unknown',
        },
        'non_claims': [
            'does_not_claim_complete_secret_detection',
            'does_not_prove_upstream_data_never_contained_secrets',
            'does_not_authorize_publication',
        ],
    }


def _count_changed_paths(before: Any, after: Any) -> int:
    if type(before) is not type(after):
        return 1
    if isinstance(before, dict):
        keys = set(before) | set(after)
        return sum(_count_changed_paths(before.get(key), after.get(key)) for key in keys)
    if isinstance(before, list):
        total = abs(len(before) - len(after))
        for left, right in zip(before, after):
            total += _count_changed_paths(left, right)
        return total
    return 0 if before == after else 1


def build_redaction_receipt(
    source_artifact: Mapping[str, Any],
    redacted_artifact: Mapping[str, Any],
    *,
    policy: Mapping[str, Any] | None = None,
    source_label: str = 'source_artifact',
    redacted_label: str = 'redacted_artifact',
    generated_at: str | None = None,
) -> Dict[str, Any]:
    """Build a public-safe receipt summarizing a redaction operation.

    The receipt records hashes and counts. It does not include raw private
    source material and does not prove a complete secret scan.
    """
    from .artifacts import artifact_sha256

    policy_doc = dict(policy or build_default_redaction_policy())
    source_hash = artifact_sha256(source_artifact)
    redacted_hash = artifact_sha256(redacted_artifact)
    changed_paths = _count_changed_paths(source_artifact, redacted_artifact)
    status = 'redacted' if source_hash != redacted_hash else 'unchanged'
    rules = json_array(policy_doc.get('rules'))
    return {
        'artifact_type': REDACTION_RECEIPT_ARTIFACT_TYPE,
        'schema_version': REDACTION_RECEIPT_SCHEMA_VERSION,
        'generated_at': generated_at or _utc_now(),
        'policy': {
            'policy_id': str(policy_doc.get('policy_id') or ''),
            'policy_hash': artifact_sha256(policy_doc),
        },
        'source': {
            'label': source_label,
            'hash': source_hash,
        },
        'redacted': {
            'label': redacted_label,
            'hash': redacted_hash,
        },
        'status': status,
        'summary': {
            'rules_considered': len(rules),
            'changed_paths_estimate': changed_paths,
            'source_and_redacted_hash_match': source_hash == redacted_hash,
        },
        'disclosure': build_disclosure_status(
            status='checks_performed',
            checks=[str(rule.get('rule_id') or '') for rule in rules if rule.get('rule_id')],
            policy=str(policy_doc.get('policy_id') or ''),
            coverage={
                'credentials': 'heuristic_checked',
                'private_paths': 'heuristic_checked',
                'raw_output': 'heuristic_checked',
            },
        ),
        'public_safety': {
            'raw_source_included': False,
            'raw_live_evidence_included': False,
            'raw_stdout_stderr_included': False,
            'credentials_included': 'unknown',
            'private_paths_included': 'unknown',
        },
        'non_claims': [
            'does_not_claim_complete_secret_detection',
            'does_not_prove_upstream_data_never_contained_secrets',
            'does_not_authorize_publication',
        ],
    }
