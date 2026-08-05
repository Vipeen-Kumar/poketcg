"""Deck-loading and deck-legality exceptions."""

from __future__ import annotations

from poketcg.shared.exceptions import DeckError


class DeckValidationError(DeckError):
    """Raised when one or more deck-legality checks fail."""

    def __init__(self, message: str, *, issues: tuple[object, ...] = ()) -> None:
        super().__init__(message)
        self.issues = issues


class DeckLoadError(DeckValidationError):
    """Raised when a deck file cannot be parsed."""


class DeckSizeError(DeckValidationError):
    """Raised when a deck does not contain the required number of cards."""


class DeckDuplicateCopyLimitError(DeckValidationError):
    """Raised when a non-exempt card appears too many times in a deck."""


class DeckAceSpecLimitError(DeckValidationError):
    """Raised when more than one ACE SPEC card appears in a deck."""


class UnknownDeckCardError(DeckValidationError):
    """Raised when a deck references a card that is unknown to the card database."""
