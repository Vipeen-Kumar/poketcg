"""Miscellaneous helper placeholders."""

from __future__ import annotations

from collections.abc import Iterable


def as_tuple(values: Iterable[object]) -> tuple[object, ...]:
    """Convert an iterable into a tuple."""

    return tuple(values)
