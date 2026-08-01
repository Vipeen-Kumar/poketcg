"""Serialization helpers used across the project."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path


def to_serializable(value: object) -> object:
    """Convert a value into a JSON-friendly structure."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.name
    if isinstance(value, Path):
        return str(value)
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return to_serializable(to_dict())
    if is_dataclass(value):
        return to_serializable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): to_serializable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [to_serializable(item) for item in value]
    if isinstance(value, list):
        return [to_serializable(item) for item in value]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [to_serializable(item) for item in value]
    return value


def serialize_placeholder(path: Path) -> Path:
    """Placeholder to anchor future serialization helpers."""

    return path
