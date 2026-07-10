from __future__ import annotations

import json
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Dict, TypeVar


ErrorT = TypeVar('ErrorT', bound=Exception)


@dataclass(frozen=True)
class VerificationLimits:
    """Finite JSON resource budgets used by every production input path."""

    max_file_bytes: int = 1_048_576
    max_total_bytes: int = 8_388_608
    max_nesting_depth: int = 64
    max_nodes: int = 100_000
    max_manifest_entries: int = 256

    def __post_init__(self) -> None:
        for name, value in (
            ('max_file_bytes', self.max_file_bytes),
            ('max_total_bytes', self.max_total_bytes),
            ('max_nesting_depth', self.max_nesting_depth),
            ('max_nodes', self.max_nodes),
            ('max_manifest_entries', self.max_manifest_entries),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f'{name} must be a positive integer')
        if self.max_total_bytes < self.max_file_bytes:
            raise ValueError('max_total_bytes must be greater than or equal to max_file_bytes')


DEFAULT_VERIFICATION_LIMITS = VerificationLimits()


class _DuplicateKeyError(ValueError):
    pass


class _NonStandardConstantError(ValueError):
    pass


@dataclass
class _JsonBudget:
    limits: VerificationLimits
    total_bytes: int = 0
    total_nodes: int = 0

    def consume(self, *, source: Path | str, byte_count: int, value: Any) -> None:
        self.total_bytes += byte_count
        if self.total_bytes > self.limits.max_total_bytes:
            raise ValueError(
                f'{source}: aggregate JSON bytes exceed '
                f'max_total_bytes={self.limits.max_total_bytes}'
            )
        node_count = _validate_structure(value, source=source, limits=self.limits)
        self.total_nodes += node_count
        if self.total_nodes > self.limits.max_nodes:
            raise ValueError(
                f'{source}: aggregate JSON structure exceeds max_nodes={self.limits.max_nodes}'
            )


def _format_json_decode_error(path: Path | str, exc: JSONDecodeError) -> str:
    return f'{path}: invalid JSON: {exc.msg} at line {exc.lineno} column {exc.colno}'


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(key)
        result[key] = value
    return result


def _reject_non_standard_constant(value: str) -> Any:
    raise _NonStandardConstantError(value)


def _validate_structure(
    value: Any,
    *,
    source: Path | str,
    limits: VerificationLimits,
) -> int:
    nodes = 0
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > limits.max_nodes:
            raise ValueError(f'{source}: JSON structure exceeds max_nodes={limits.max_nodes}')
        if depth > limits.max_nesting_depth:
            raise ValueError(
                f'{source}: JSON nesting exceeds max_nesting_depth={limits.max_nesting_depth}'
            )
        if isinstance(current, dict):
            stack.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list):
            stack.extend((item, depth + 1) for item in current)
    return nodes


def _decode_json(
    raw: bytes,
    *,
    source: Path | str,
    error_cls: type[ErrorT],
    limits: VerificationLimits,
    budget: _JsonBudget | None,
) -> Any:
    if len(raw) > limits.max_file_bytes:
        raise error_cls(f'{source}: JSON file exceeds max_file_bytes={limits.max_file_bytes}')
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise error_cls(f'{source}: invalid JSON: input is not valid UTF-8') from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_standard_constant,
        )
    except JSONDecodeError as exc:
        raise error_cls(_format_json_decode_error(source, exc)) from exc
    except _DuplicateKeyError as exc:
        raise error_cls(f'{source}: invalid JSON: duplicate object key {exc.args[0]!r}') from exc
    except _NonStandardConstantError as exc:
        raise error_cls(f'{source}: invalid JSON: non-standard number {exc.args[0]!r}') from exc
    try:
        if budget is None:
            _validate_structure(value, source=source, limits=limits)
        else:
            budget.consume(source=source, byte_count=len(raw), value=value)
    except ValueError as exc:
        raise error_cls(str(exc)) from exc
    return value


def load_json_document(
    path: Path | str,
    *,
    error_cls: type[ErrorT],
    limits: VerificationLimits | None = None,
    budget: _JsonBudget | None = None,
    max_bytes: int | None = None,
) -> tuple[bytes, Any]:
    json_path = Path(path)
    policy = limits or DEFAULT_VERIFICATION_LIMITS
    if max_bytes is not None:
        policy = VerificationLimits(
            max_file_bytes=max_bytes,
            max_total_bytes=max(policy.max_total_bytes, max_bytes),
            max_nesting_depth=policy.max_nesting_depth,
            max_nodes=policy.max_nodes,
            max_manifest_entries=policy.max_manifest_entries,
        )
    try:
        raw = json_path.read_bytes()
    except OSError as exc:
        detail = exc.strerror or str(exc)
        raise error_cls(f'{json_path}: cannot read JSON: {detail}') from exc
    if max_bytes is not None and len(raw) > max_bytes:
        raise error_cls(f'{json_path}: JSON file exceeds max_bytes={max_bytes}')
    return raw, _decode_json(
        raw,
        source=json_path,
        error_cls=error_cls,
        limits=policy,
        budget=budget,
    )


def load_json_value(
    path: Path | str,
    *,
    error_cls: type[ErrorT],
    max_bytes: int | None = None,
    limits: VerificationLimits | None = None,
    budget: _JsonBudget | None = None,
) -> Any:
    _raw, value = load_json_document(
        path,
        error_cls=error_cls,
        max_bytes=max_bytes,
        limits=limits,
        budget=budget,
    )
    return value


def validate_json_value(
    value: Any,
    *,
    source: Path | str,
    error_cls: type[ErrorT],
    limits: VerificationLimits | None = None,
    budget: _JsonBudget | None = None,
) -> None:
    policy = limits or DEFAULT_VERIFICATION_LIMITS
    try:
        if budget is None:
            _validate_structure(value, source=source, limits=policy)
        else:
            budget.consume(source=source, byte_count=0, value=value)
    except ValueError as exc:
        raise error_cls(str(exc)) from exc


def load_json_object(
    path: Path | str,
    *,
    error_cls: type[ErrorT],
    max_bytes: int | None = None,
    limits: VerificationLimits | None = None,
    budget: _JsonBudget | None = None,
) -> Dict[str, Any]:
    value = load_json_value(
        path,
        error_cls=error_cls,
        max_bytes=max_bytes,
        limits=limits,
        budget=budget,
    )
    if not isinstance(value, dict):
        raise error_cls(f'{Path(path)}: JSON root is not an object')
    return value


def parse_json_object(
    text: str,
    *,
    source: str,
    error_cls: type[ErrorT],
    limits: VerificationLimits | None = None,
) -> Dict[str, Any]:
    policy = limits or DEFAULT_VERIFICATION_LIMITS
    value = _decode_json(
        text.encode('utf-8'),
        source=source,
        error_cls=error_cls,
        limits=policy,
        budget=None,
    )
    if not isinstance(value, dict):
        raise error_cls(f'{source}: JSON root is not an object')
    return value
