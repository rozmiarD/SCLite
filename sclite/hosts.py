from __future__ import annotations

from typing import Any, Iterable, List
from urllib.parse import urlparse
import warnings


def _safe_str(value: Any) -> str:
    return str(value or '')


def extract_host(value: Any) -> str:
    """Extract a normalized DNS host from a URL/header-ish scalar.

    This is intentionally small and dependency-free. It is a static review aid,
    not a full scope-authorization engine and not a DNS/redirect resolver.
    """
    warnings.warn(
        'sclite.hosts.extract_host is a legacy host adapter; normalize targets in the host',
        DeprecationWarning,
        stacklevel=2,
    )
    text = _safe_str(value).strip()
    if not text:
        return ''
    lowered = text.lower()
    for prefix in ('host:', 'origin:', 'referer:', 'authority:'):
        if lowered.startswith(prefix):
            text = text[len(prefix):].strip()
            lowered = text.lower()
            break
    parsed = urlparse(text)
    host = _safe_str(parsed.hostname).strip().lower()
    if not host and '://' not in text:
        token = text.strip("\"'`()[]{}<>,;")
        if not token or token.startswith('-'):
            return ''
        if '@' in token:
            return ''
        parsed = urlparse('//' + token)
        host = _safe_str(parsed.hostname).strip().lower()
    if host.startswith('*.'):
        host = host[2:]
    if not host or '.' not in host:
        return ''
    if any(ch.isspace() for ch in host):
        return ''
    allowed = set('abcdefghijklmnopqrstuvwxyz0123456789.-')
    if any(ch not in allowed for ch in host):
        return ''
    return host


def collect_hosts_from_scalars(values: Iterable[Any]) -> List[str]:
    hosts: List[str] = []
    seen: set[str] = set()
    for value in values:
        host = extract_host(value)
        if host and host not in seen:
            seen.add(host)
            hosts.append(host)
    return hosts
