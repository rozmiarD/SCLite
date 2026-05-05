from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


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
    if isinstance(value, dict):
        if isinstance(value.get('name'), str) and ('value' in value or 'raw' in value):
            out = {k: sanitize_public_artifact(v) for k, v in value.items()}
            out['value'] = PUBLIC_REDACTION_PLACEHOLDER
            if 'raw' in out:
                out['raw'] = f"{value.get('name')}: {PUBLIC_REDACTION_PLACEHOLDER}"
            return out
        out: Dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key or '').lower()
            if key_text in SENSITIVE_VALUE_KEYS and item:
                out[key] = PUBLIC_REDACTION_PLACEHOLDER
            elif key_text in {'stdout', 'stderr'}:
                out[key] = '' if not item else '<omitted_for_public_demo>'
            else:
                out[key] = sanitize_public_artifact(item)
        return out
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
