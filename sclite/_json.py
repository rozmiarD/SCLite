from __future__ import annotations

import json
import math
import os
import stat
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
    max_inventory_entries: int = 1_024
    max_directory_depth: int = 16
    max_path_bytes: int = 65_536

    def __post_init__(self) -> None:
        for name, value in (
            ('max_file_bytes', self.max_file_bytes),
            ('max_total_bytes', self.max_total_bytes),
            ('max_nesting_depth', self.max_nesting_depth),
            ('max_nodes', self.max_nodes),
            ('max_manifest_entries', self.max_manifest_entries),
            ('max_inventory_entries', self.max_inventory_entries),
            ('max_directory_depth', self.max_directory_depth),
            ('max_path_bytes', self.max_path_bytes),
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
        elif isinstance(current, float) and not math.isfinite(current):
            raise ValueError(f'{source}: JSON number is not finite')
        elif isinstance(current, str):
            try:
                current.encode('utf-8')
            except UnicodeEncodeError as exc:
                raise ValueError(f'{source}: JSON string contains an invalid Unicode surrogate') from exc
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
    except RecursionError as exc:
        raise error_cls(f'{source}: JSON nesting exceeds parser safety limit') from exc
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
    root: Path | None = None,
    relative_path: str | None = None,
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
            max_inventory_entries=policy.max_inventory_entries,
            max_directory_depth=policy.max_directory_depth,
            max_path_bytes=policy.max_path_bytes,
        )
    read_limit = policy.max_file_bytes
    flags = os.O_RDONLY | getattr(os, 'O_CLOEXEC', 0) | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    descriptor = -1
    parent_descriptor = -1
    try:
        if root is not None and relative_path is not None:
            parts = Path(relative_path).parts
            if not parts or Path(relative_path).is_absolute() or '..' in parts:
                raise error_cls('JSON path escapes trusted root')
            parent_descriptor = os.open(root, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | getattr(os, 'O_NOFOLLOW', 0))
            for part in parts[:-1]:
                next_descriptor = os.open(part, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | getattr(os, 'O_NOFOLLOW', 0), dir_fd=parent_descriptor)
                os.close(parent_descriptor)
                parent_descriptor = next_descriptor
            descriptor = os.open(parts[-1], flags, dir_fd=parent_descriptor)
        else:
            descriptor = os.open(json_path, flags)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise error_cls(f'{json_path}: JSON input is not a regular file')
        if metadata.st_nlink != 1:
            raise error_cls(f'{json_path}: JSON input must have exactly one hard link')
        limit_label = f'max_bytes={max_bytes}' if max_bytes is not None else f'max_file_bytes={read_limit}'
        if metadata.st_size > read_limit:
            raise error_cls(f'{json_path}: JSON file exceeds {limit_label}')
        chunks: list[bytes] = []
        remaining = read_limit + 1
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b''.join(chunks)
        if len(raw) > read_limit:
            raise error_cls(f'{json_path}: JSON file exceeds {limit_label}')
    except OSError as exc:
        detail = exc.strerror or str(exc)
        raise error_cls(f'{json_path}: cannot read JSON: {detail}') from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if parent_descriptor >= 0:
            os.close(parent_descriptor)
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
    root: Path | None = None,
    relative_path: str | None = None,
) -> Any:
    _raw, value = load_json_document(
        path,
        error_cls=error_cls,
        max_bytes=max_bytes,
        limits=limits,
        budget=budget,
        root=root,
        relative_path=relative_path,
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
    root: Path | None = None,
    relative_path: str | None = None,
) -> Dict[str, Any]:
    value = load_json_value(
        path,
        error_cls=error_cls,
        max_bytes=max_bytes,
        limits=limits,
        budget=budget,
        root=root,
        relative_path=relative_path,
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
