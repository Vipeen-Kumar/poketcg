"""Deck loading and legality validation."""

from .exceptions import (
    DeckAceSpecLimitError,
    DeckDuplicateCopyLimitError,
    DeckLoadError,
    DeckSizeError,
    DeckValidationError,
    UnknownDeckCardError,
)
from .loader import DeckLoader
from .models import DeckValidationContext, DeckValidationIssue, DeckValidationResult
from .rules import BaseDeckValidationRule, AceSpecLimitRule, DeckCopyLimitRule, DeckSizeRule
from .validator import DeckValidator

__all__ = [
    "AceSpecLimitRule",
    "BaseDeckValidationRule",
    "DeckAceSpecLimitError",
    "DeckCopyLimitRule",
    "DeckDuplicateCopyLimitError",
    "DeckLoadError",
    "DeckLoader",
    "DeckSizeError",
    "DeckSizeRule",
    "DeckValidationContext",
    "DeckValidationError",
    "DeckValidationIssue",
    "DeckValidationResult",
    "DeckValidator",
    "UnknownDeckCardError",
]
