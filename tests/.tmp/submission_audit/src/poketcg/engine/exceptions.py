"""Observation-parser-specific exceptions."""

from __future__ import annotations

from poketcg.shared.exceptions import InvalidObservationError, ParserError


class MissingObservationFieldError(InvalidObservationError):
    """Raised when a required observation field is missing."""


class InvalidObservationEnumError(InvalidObservationError):
    """Raised when an observation enum value is unknown or invalid."""


class CorruptedObservationError(InvalidObservationError):
    """Raised when the observation structure is internally inconsistent."""


class MissingObservationCardError(ParserError):
    """Raised when a card id referenced by the observation does not exist in CardDatabase."""
