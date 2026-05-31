from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Dict, TypeVar


ErrorT = TypeVar('ErrorT', bound=Exception)


def _format_json_decode_error(path: Path | str, exc: JSONDecodeError) -> str:
    return f'{path}: invalid JSON: {exc.msg} at line {exc.lineno} column {exc.colno}'


def load_json_value(path: Path | str, *, error_cls: type[ErrorT]) -> Any:
    json_path = Path(path)
    try:
        raw = json_path.read_text(encoding='utf-8')
    except OSError as exc:
        detail = exc.strerror or str(exc)
        raise error_cls(f'{json_path}: cannot read JSON: {detail}') from exc
    try:
        return json.loads(raw)
    except JSONDecodeError as exc:
        raise error_cls(_format_json_decode_error(json_path, exc)) from exc


def load_json_object(path: Path | str, *, error_cls: type[ErrorT]) -> Dict[str, Any]:
    value = load_json_value(path, error_cls=error_cls)
    if not isinstance(value, dict):
        raise error_cls(f'{Path(path)}: JSON root is not an object')
    return value


def parse_json_object(text: str, *, source: str, error_cls: type[ErrorT]) -> Dict[str, Any]:
    try:
        value = json.loads(text)
    except JSONDecodeError as exc:
        raise error_cls(_format_json_decode_error(source, exc)) from exc
    if not isinstance(value, dict):
        raise error_cls(f'{source}: JSON root is not an object')
    return value
