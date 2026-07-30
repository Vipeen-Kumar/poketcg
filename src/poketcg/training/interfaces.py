"""Training interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BaseTrainer(ABC):
    """Abstract training orchestration interface."""

    @abstractmethod
    def train(self) -> None:
        """Run a training workflow."""

    @abstractmethod
    def save_checkpoint(self, path: Path) -> None:
        """Save trainer state to a checkpoint path."""
