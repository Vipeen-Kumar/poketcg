"""Interfaces for card metadata access and persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from .models import CardData


class BaseCardCatalog(ABC):
    """Abstract card metadata provider."""

    @abstractmethod
    def get(self, card_id: int) -> CardData:
        """Return metadata for a card id."""

    @abstractmethod
    def exists(self, card_id: int) -> bool:
        """Return whether the card id is known."""

    @abstractmethod
    def all_cards(self) -> Iterable[CardData]:
        """Iterate over all known card metadata."""


class BaseCardDataSource(ABC):
    """Abstract source of raw card data rows."""

    @abstractmethod
    def load_rows(self) -> Sequence[Mapping[str, str]]:
        """Load raw card rows from a source."""


class BaseCardDataCache(ABC):
    """Abstract future cache interface for normalized card data."""

    @abstractmethod
    def exists(self, path: Path) -> bool:
        """Return whether a cache artifact exists."""

    @abstractmethod
    def load(self, path: Path) -> Sequence[CardData]:
        """Load normalized card data from cache."""

    @abstractmethod
    def save(self, path: Path, cards: Sequence[CardData]) -> None:
        """Save normalized card data to cache."""
