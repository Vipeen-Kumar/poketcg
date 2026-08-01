"""Agent interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from poketcg.domain.models import ActionSelection, Deck, Observation


class BaseAgent(ABC):
    """Top-level agent contract."""

    @abstractmethod
    def select_deck(self) -> Deck:
        """Return the deck to use for a battle."""

    @abstractmethod
    def act(self, observation: Observation) -> ActionSelection:
        """Choose an action for the given observation."""
