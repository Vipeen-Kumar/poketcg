"""RL interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from poketcg.domain.models import Observation


class BaseReplayBuffer(ABC):
    """Abstract replay-buffer contract."""

    @abstractmethod
    def add(self, observation: Observation) -> None:
        """Store an observation or transition payload."""

    @abstractmethod
    def __len__(self) -> int:
        """Return the number of stored items."""


class BaseSelfPlayRunner(ABC):
    """Abstract self-play execution contract."""

    @abstractmethod
    def run(self, num_episodes: int) -> Iterable[Observation]:
        """Run self-play episodes and yield recorded outputs."""
