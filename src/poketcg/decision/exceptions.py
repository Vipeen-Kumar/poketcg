"""Decision-engine exceptions."""

from __future__ import annotations

from poketcg.shared.exceptions import PokeTCGError


class DecisionError(PokeTCGError):
    """Base exception for decision-engine failures."""


class InvalidRuleError(DecisionError):
    """Raised when a rule instance is malformed."""


class DuplicateRuleNameError(DecisionError):
    """Raised when two rules share the same name."""


class CircularPriorityError(DecisionError):
    """Raised when rule ordering constraints contain a cycle."""


class MissingFallbackRuleError(DecisionError):
    """Raised when the registry has no enabled fallback rule."""


class EmptyLegalActionError(DecisionError):
    """Raised when the engine is asked to choose from an empty action list."""


class DecisionConfigurationError(DecisionError):
    """Raised when decision configuration is invalid."""


class UnknownRuleError(DecisionConfigurationError):
    """Raised when configuration references an unknown rule."""