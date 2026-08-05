"""Load deck.csv files into typed deck models."""

from __future__ import annotations

from pathlib import Path

from poketcg.cards import CardDatabase
from poketcg.domain import Deck

from .exceptions import DeckLoadError
from .validator import DeckValidator


class DeckLoader:
    """Load and validate a deck from a CSV-style text file."""

    def __init__(self, card_database: CardDatabase, *, validator: DeckValidator | None = None) -> None:
        self._card_database = card_database
        self._validator = validator or DeckValidator(card_database)

    def load(self, path: Path) -> Deck:
        """Load a deck file and validate it against the configured rules."""

        if not path.exists():
            raise DeckLoadError(f"Missing deck file: {path}")

        card_ids: list[int] = []
        for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                card_ids.append(int(stripped))
            except ValueError as error:
                raise DeckLoadError(f"Invalid card id on line {line_number}: {stripped!r}") from error

        deck = Deck(card_ids=tuple(card_ids), name=path.stem)
        self._validator.validate_or_raise(deck)
        return deck

