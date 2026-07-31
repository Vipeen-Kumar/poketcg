"""Supporter rule."""

from __future__ import annotations

from time import perf_counter

from poketcg.actions import PlayCardAction

from poketcg.decision.context import DecisionContext
from poketcg.decision.results import RuleResult

from .base import BaseRule


class SupporterRule(BaseRule):
    """Select a legal Supporter play when one is available."""

    rule_name = "SupporterRule"
    description = "Choose the first legal supporter play action."
    default_priority = 600

    def applies(self, context: DecisionContext) -> bool:
        return not context.observation.supporter_played and any(
            isinstance(action, PlayCardAction) and action.card.metadata.is_supporter() for action in context.analyzer.play_actions()
        )

    def evaluate(self, context: DecisionContext) -> RuleResult:
        start = perf_counter()
        actions = tuple(
            action
            for action in context.analyzer.play_actions()
            if isinstance(action, PlayCardAction) and action.card.metadata.is_supporter()
        )
        if not actions:
            return self._result(
                passed=False,
                action=None,
                reason="No supporter action available.",
                metadata={"available_supporter_actions": 0},
                execution_time=perf_counter() - start,
            )
        return self._result(
            passed=True,
            action=actions[0],
            reason="Supporter play is available.",
            metadata={"available_supporter_actions": len(actions)},
            execution_time=perf_counter() - start,
        )
