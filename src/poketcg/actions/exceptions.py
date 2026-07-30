"""Action-layer exceptions."""

from __future__ import annotations

from poketcg.shared.exceptions import InvalidActionError


class ActionFactoryError(InvalidActionError):
    """Base exception for action-factory failures."""


class ActionValidationError(ActionFactoryError):
    """Raised when a parsed option lacks required fields for a typed action."""


class CorruptedActionError(ActionFactoryError):
    """Raised when a parsed selection is structurally inconsistent."""
