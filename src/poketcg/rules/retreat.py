"""Retreat rule."""

from __future__ import annotations

from time import perf_counter

from poketcg.actions import RetreatAction

from poketcg.decision.context import DecisionContext
from poketcg.decision.results import RuleResult

from .base import BaseRule


class RetreatRule(BaseRule):
    """Select a legal retreat action when retreat is available."""

    rule_name = "RetreatRule"
    description = "Choose the first legal retreat action."
    default_priority = 300

    def applies(self, context: DecisionContext) -> bool:
        return context.analyzer.can_retreat() and bool(context.analyzer.retreat_actions())

    def evaluate(self, context: DecisionContext) -> RuleResult:
        start = perf_counter()
        actions = tuple(action for action in context.analyzer.retreat_actions() if isinstance(action, RetreatAction))
        if not actions:
            return self._result(
                passed=False,
                action=None,
                reason="No retreat action available.",
                metadata={"available_retreat_actions": 0},
                execution_time=perf_counter() - start,
            )
        return self._result(
            passed=True,
            action=actions[0],
            reason="Retreat is available.",
            metadata={"available_retreat_actions": len(actions)},
            execution_time=perf_counter() - start,
        )
