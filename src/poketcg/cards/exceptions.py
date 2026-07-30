"""Exceptions specific to the cards package."""

from __future__ import annotations

from poketcg.shared.exceptions import PokeTCGError


class CardDatabaseError(PokeTCGError):
    """Base exception for card database failures."""


class CardDatabaseNotLoadedError(CardDatabaseError):
    """Raised when a database is queried before loading."""


class CardDataValidationError(CardDatabaseError):
    """Raised when source card data fails validation."""


class DuplicateCardIdError(CardDataValidationError):
    """Raised when duplicate card ids are encountered unexpectedly."""


class MissingCardIdError(CardDataValidationError):
    """Raised when a card id is missing or invalid."""


class CorruptedCardRowError(CardDataValidationError):
    """Raised when a row is malformed or internally inconsistent."""


class UnknownCardLookupError(CardDatabaseError):
    """Raised when a requested card id does not exist."""
