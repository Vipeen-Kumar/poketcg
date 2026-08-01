"""Shared rule-library base classes."""

from __future__ import annotations

from poketcg.decision.engine import BaseRule as DecisionBaseRule


class BaseRule(DecisionBaseRule):
    """Base class for Pokémon rule-library rules."""

    description: str = ""
