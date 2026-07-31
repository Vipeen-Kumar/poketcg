"""Ability rule."""

from __future__ import annotations

from time import perf_counter

from poketcg.actions import AbilityAction

from poketcg.decision.context import DecisionContext
from poketcg.decision.results import RuleResult

from .base import BaseRule


class AbilityRule(BaseRule):
    """Select a legal ability action when one is available."""

    rule_name = "AbilityRule"
    description = "Choose the first legal ability action."
    default_priority = 450

    def applies(self, context: DecisionContext) -> bool:
        return bool(context.analyzer.ability_actions())

    def evaluate(self, context: DecisionContext) -> RuleResult:
        start = perf_counter()
        actions = tuple(action for action in context.analyzer.ability_actions() if isinstance(action, AbilityAction))
        if not actions:
            return self._result(
                passed=False,
                action=None,
                reason="No ability action available.",
                metadata={"available_ability_actions": 0},
                execution_time=perf_counter() - start,
            )
        return self._result(
            passed=True,
            action=actions[0],
            reason="Ability action is available.",
            metadata={"available_ability_actions": len(actions)},
            execution_time=perf_counter() - start,
        )
