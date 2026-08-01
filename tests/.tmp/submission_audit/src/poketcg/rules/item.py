"""Item rule."""

from __future__ import annotations

from time import perf_counter

from poketcg.actions import PlayCardAction

from poketcg.decision.context import DecisionContext
from poketcg.decision.results import RuleResult

from .base import BaseRule


class ItemRule(BaseRule):
    """Select a legal Item play when one is available."""

    rule_name = "ItemRule"
    description = "Choose the first legal item play action."
    default_priority = 500

    def applies(self, context: DecisionContext) -> bool:
        return any(isinstance(action, PlayCardAction) and action.card.metadata.is_item() for action in context.analyzer.play_actions())

    def evaluate(self, context: DecisionContext) -> RuleResult:
        start = perf_counter()
        actions = tuple(
            action
            for action in context.analyzer.play_actions()
            if isinstance(action, PlayCardAction) and action.card.metadata.is_item()
        )
        if not actions:
            return self._result(
                passed=False,
                action=None,
                reason="No item action available.",
                metadata={"available_item_actions": 0},
                execution_time=perf_counter() - start,
            )
        return self._result(
            passed=True,
            action=actions[0],
            reason="Item play is available.",
            metadata={"available_item_actions": len(actions)},
            execution_time=perf_counter() - start,
        )
