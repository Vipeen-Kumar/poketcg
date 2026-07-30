"""Timing helper placeholders."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter


@dataclass(slots=True)
class TimerSnapshot:
    started_at: float
    ended_at: float | None = None


def now() -> float:
    """Return a high-resolution monotonic timestamp."""

    return perf_counter()
