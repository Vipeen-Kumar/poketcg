"""Evaluation interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Mapping, Sequence

from poketcg.agent.interfaces import BaseAgent


class BaseEvaluator(ABC):
    """Abstract evaluator contract."""

    @abstractmethod
    def evaluate(self, agents: Sequence[BaseAgent]) -> Mapping[str, float]:
        """Evaluate one or more agents and return summary metrics."""
