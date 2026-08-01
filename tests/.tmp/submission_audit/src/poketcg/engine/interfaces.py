"""Interfaces for environment parsing and translation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Mapping, Sequence

from poketcg.domain.models import ActionSelection, LegalAction, Observation


class BaseObservationParser(ABC):
    """Parse raw environment payloads into internal observation models."""

    @abstractmethod
    def parse(self, payload: Mapping[str, object]) -> Observation:
        """Parse a raw observation payload."""


class BaseActionTranslator(ABC):
    """Translate internal action selections into environment action payloads."""

    @abstractmethod
    def to_environment_action(self, selection: ActionSelection) -> Sequence[int]:
        """Translate a selected action into runtime indices."""


class BaseEnvironmentAdapter(ABC):
    """Bridge for environment-specific runtime behavior."""

    @abstractmethod
    def parse_observation(self, payload: Mapping[str, object]) -> Observation:
        """Parse a raw observation payload."""

    @abstractmethod
    def list_legal_actions(self, observation: Observation) -> Sequence[LegalAction]:
        """Return legal actions derived from an observation."""

    @abstractmethod
    def build_runtime_action(self, selection: ActionSelection) -> Sequence[int]:
        """Build the final runtime action payload."""
