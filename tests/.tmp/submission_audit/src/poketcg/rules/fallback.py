"""Fallback rule."""

from __future__ import annotations

from time import perf_counter

from poketcg.decision.context import DecisionContext
from poketcg.decision.results import RuleResult

from .base import BaseRule


class FallbackRule(BaseRule):
    """Safety rule that always returns a legal action."""

    rule_name = "FallbackRule"
    description = "Choose End Turn when legal, otherwise the first legal action."
    default_priority = -1000
    is_fallback = True

    def applies(self, context: DecisionContext) -> bool:
        return bool(context.legal_actions)

    def evaluate(self, context: DecisionContext) -> RuleResult:
        start = perf_counter()
        if not context.legal_actions:
            return self._result(
                passed=False,
                action=None,
                reason="No legal actions are available for fallback selection.",
                metadata={"legal_action_count": 0},
                execution_time=perf_counter() - start,
            )

        end_turn_action = context.analyzer.end_turn_action()
        action = end_turn_action or context.legal_actions[0]
        reason = "Fallback selected End Turn." if end_turn_action is not None else "Fallback selected the first legal action."
        return self._result(
            passed=True,
            action=action,
            reason=reason,
            metadata={"legal_action_count": len(context.legal_actions), "fallback": True},
            execution_time=perf_counter() - start,
        )
