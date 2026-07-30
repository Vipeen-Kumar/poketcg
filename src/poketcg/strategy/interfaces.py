"""Strategy and policy interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from poketcg.domain.models import ActionSelection, LegalAction, Observation


class BasePolicy(ABC):
    """Policy abstraction for ranking or choosing legal actions."""

    @abstractmethod
    def select_action(
        self,
        observation: Observation,
        legal_actions: Sequence[LegalAction],
    ) -> ActionSelection:
        """Select an action from the legal action set."""


class BaseStrategy(ABC):
    """Higher-level strategy abstraction."""

    @abstractmethod
    def choose_action(
        self,
        observation: Observation,
        legal_actions: Sequence[LegalAction],
    ) -> ActionSelection:
        """Choose an action for the current game situation."""
