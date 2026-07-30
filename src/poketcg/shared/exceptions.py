"""Custom project exceptions."""

from __future__ import annotations


class PokeTCGError(Exception):
    """Base exception for the project."""


class ParserError(PokeTCGError):
    """Raised when parsing fails."""


class InvalidObservationError(ParserError):
    """Raised when an observation payload is invalid or incomplete."""


class InvalidActionError(PokeTCGError):
    """Raised when an action payload is invalid."""


class UnknownCardError(PokeTCGError):
    """Raised when a card id is unknown to the catalog."""


class DeckError(PokeTCGError):
    """Raised when deck structure or deck contents are invalid."""


class ConfigurationError(PokeTCGError):
    """Raised when project configuration is invalid."""


class SerializationError(PokeTCGError):
    """Raised when serialization or deserialization fails."""
