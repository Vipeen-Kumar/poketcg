"""Randomness helper placeholders."""

from __future__ import annotations

import random


def build_rng(seed: int) -> random.Random:
    """Return a dedicated random number generator."""

    return random.Random(seed)
