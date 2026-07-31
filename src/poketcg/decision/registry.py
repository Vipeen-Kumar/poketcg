"""Rule registry and loading helpers."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from copy import deepcopy
from importlib import import_module
from typing import Protocol, runtime_checkable

from .exceptions import DecisionConfigurationError, DuplicateRuleNameError, InvalidRuleError, MissingFallbackRuleError, UnknownRuleError
from .priority import sort_rules


@runtime_checkable
class RuleProtocol(Protocol):
    """Minimal interface required by the registry."""

    name: str
    priority: int
    enabled: bool
    runs_before: tuple[str, ...]
    runs_after: tuple[str, ...]
    is_fallback: bool

    def applies(self, context: object) -> bool:
        """Return whether the rule can run in the provided context."""

    def evaluate(self, context: object) -> object:
        """Return the rule result for the provided context."""

    def enable(self) -> None:
        """Enable the rule."""

    def disable(self) -> None:
        """Disable the rule."""


class RuleRegistry:
    """Own every registered rule instance."""

    def __init__(self, rules: Sequence[RuleProtocol] | None = None) -> None:
        self._rules: dict[str, RuleProtocol] = {}
        if rules is not None:
            for rule in rules:
                self.register(rule)

    def register(self, rule: RuleProtocol) -> RuleProtocol:
        """Add a rule to the registry."""

        self._validate_rule(rule)
        if rule.name in self._rules:
            raise DuplicateRuleNameError(f"Rule {rule.name} is already registered.")
        self._rules[rule.name] = rule
        return rule

    def unregister(self, rule_name: str) -> RuleProtocol:
        """Remove a rule from the registry."""

        try:
            return self._rules.pop(rule_name)
        except KeyError as error:
            raise UnknownRuleError(f"Rule {rule_name} is not registered.") from error

    def get(self, rule_name: str) -> RuleProtocol:
        """Return a rule by name."""

        try:
            return self._rules[rule_name]
        except KeyError as error:
            raise UnknownRuleError(f"Rule {rule_name} is not registered.") from error

    def enable(self, rule_name: str) -> RuleProtocol:
        """Enable a registered rule."""

        rule = self.get(rule_name)
        rule.enable()
        return rule

    def disable(self, rule_name: str) -> RuleProtocol:
        """Disable a registered rule."""

        rule = self.get(rule_name)
        rule.disable()
        return rule

    def all_rules(self) -> tuple[RuleProtocol, ...]:
        """Return every registered rule."""

        return tuple(self._rules.values())

    def ordered_rules(self, *, include_fallback: bool = False) -> tuple[RuleProtocol, ...]:
        """Return enabled rules in priority order."""

        rules = [rule for rule in self._rules.values() if rule.enabled]
        if not include_fallback:
            rules = [rule for rule in rules if not rule.is_fallback]
        return sort_rules(rules)

    def fallback_rule(self) -> RuleProtocol:
        """Return the enabled fallback rule."""

        fallbacks = [rule for rule in self._rules.values() if rule.enabled and rule.is_fallback]
        if not fallbacks:
            raise MissingFallbackRuleError("No enabled fallback rule is registered.")
        if len(fallbacks) > 1:
            raise DecisionConfigurationError("Multiple fallback rules are registered.")
        return fallbacks[0]

    def load_modules(self, module_names: Iterable[str]) -> None:
        """Import plugin modules so they can self-register."""

        for module_name in module_names:
            import_module(module_name)

    def copy(self) -> "RuleRegistry":
        """Return a deep-copied registry snapshot."""

        return RuleRegistry(deepcopy(self.all_rules()))

    def _validate_rule(self, rule: RuleProtocol) -> None:
        if not isinstance(rule.name, str) or not rule.name.strip():
            raise InvalidRuleError("Registered rules must have a non-empty name.")
        if not isinstance(rule.priority, int):
            raise InvalidRuleError(f"Rule {rule.name} has an invalid priority value.")
        if not isinstance(rule.enabled, bool):
            raise InvalidRuleError(f"Rule {rule.name} has an invalid enabled flag.")
        if not callable(getattr(rule, "applies", None)) or not callable(getattr(rule, "evaluate", None)):
            raise InvalidRuleError(f"Rule {rule.name} does not implement the required methods.")


DEFAULT_RULE_REGISTRY = RuleRegistry()


def get_default_registry() -> RuleRegistry:
    """Return the shared rule registry used for auto-registered rules."""

    return DEFAULT_RULE_REGISTRY


def register_default_rule(rule: RuleProtocol) -> RuleProtocol:
    """Register a rule with the shared registry."""

    return DEFAULT_RULE_REGISTRY.register(rule)
