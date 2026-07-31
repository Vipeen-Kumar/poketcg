"""Deterministic decision-engine helpers."""

from .context import DecisionContext, DecisionEngineConfig, DecisionTraceRecorder
from .engine import AlwaysEndTurnRule, BaseRule, DecisionEngine, FirstLegalActionRule, FallbackRule
from .exceptions import (
    CircularPriorityError,
    DecisionConfigurationError,
    DecisionError,
    DuplicateRuleNameError,
    EmptyLegalActionError,
    InvalidRuleError,
    MissingFallbackRuleError,
    UnknownRuleError,
)
from .registry import DEFAULT_RULE_REGISTRY, RuleRegistry, get_default_registry, register_default_rule
from .results import DecisionOutcome, DecisionTrace, RuleResult

__all__ = [
    "AlwaysEndTurnRule",
    "BaseRule",
    "CircularPriorityError",
    "DecisionConfigurationError",
    "DecisionContext",
    "DecisionEngine",
    "DecisionEngineConfig",
    "DecisionError",
    "DecisionOutcome",
    "DecisionTrace",
    "DecisionTraceRecorder",
    "DuplicateRuleNameError",
    "EmptyLegalActionError",
    "FallbackRule",
    "FirstLegalActionRule",
    "InvalidRuleError",
    "MissingFallbackRuleError",
    "DEFAULT_RULE_REGISTRY",
    "RuleRegistry",
    "RuleResult",
    "UnknownRuleError",
    "get_default_registry",
    "register_default_rule",
]
