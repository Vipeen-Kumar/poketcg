"""Search interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from poketcg.domain.models import ActionSelection, LegalAction, Observation


class BaseSearch(ABC):
    """Abstract search/planning interface."""

    @abstractmethod
    def plan(
        self,
        observation: Observation,
        legal_actions: Sequence[LegalAction],
    ) -> ActionSelection:
        """Return a planned action selection."""
