"""Encoder interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Hashable, Sequence

from poketcg.domain.models import LegalAction, Observation


class BaseEncoder(ABC):
    """Generic encoder interface."""

    @abstractmethod
    def encode(self, value: object) -> Hashable:
        """Encode a value into a model-friendly representation."""


class BaseObservationEncoder(ABC):
    """Observation encoder interface."""

    @abstractmethod
    def encode_observation(self, observation: Observation) -> Hashable:
        """Encode an observation."""


class BaseActionEncoder(ABC):
    """Action encoder interface."""

    @abstractmethod
    def encode_actions(self, legal_actions: Sequence[LegalAction]) -> Hashable:
        """Encode legal actions."""
