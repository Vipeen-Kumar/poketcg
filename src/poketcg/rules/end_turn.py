"""End-turn rule."""

from __future__ import annotations

from time import perf_counter

from poketcg.actions import EndTurnAction

from poketcg.decision.context import DecisionContext
from poketcg.decision.results import RuleResult

from .base import BaseRule


class EndTurnRule(BaseRule):
    """Select the legal end-turn action when it exists."""

    rule_name = "EndTurnRule"
    description = "Choose the legal end-turn action."
    default_priority = 100

    def applies(self, context: DecisionContext) -> bool:
        return context.analyzer.end_turn_action() is not None

    def evaluate(self, context: DecisionContext) -> RuleResult:
        start = perf_counter()
        action = context.analyzer.end_turn_action()
        if action is None:
            return self._result(
                passed=False,
                action=None,
                reason="End turn is unavailable.",
                metadata={"available_end_turn_actions": 0},
                execution_time=perf_counter() - start,
            )
        if not isinstance(action, EndTurnAction):
            return self._result(
                passed=False,
                action=None,
                reason="End turn action has an unexpected type.",
                metadata={"available_end_turn_actions": 1},
                execution_time=perf_counter() - start,
            )
        return self._result(
            passed=True,
            action=action,
            reason="End turn is legal.",
            metadata={"available_end_turn_actions": 1},
            execution_time=perf_counter() - start,
        )
