"""Stadium rule."""

from __future__ import annotations

from time import perf_counter

from poketcg.actions import PlayCardAction

from poketcg.decision.context import DecisionContext
from poketcg.decision.results import RuleResult

from .base import BaseRule


class StadiumRule(BaseRule):
    """Select a legal Stadium play when one is available."""

    rule_name = "StadiumRule"
    description = "Choose the first legal stadium play action."
    default_priority = 400

    def applies(self, context: DecisionContext) -> bool:
        state = context.observation.state
        if state is None or state.stadium_played:
            return False
        return any(isinstance(action, PlayCardAction) and action.card.metadata.is_stadium() for action in context.analyzer.play_actions())

    def evaluate(self, context: DecisionContext) -> RuleResult:
        start = perf_counter()
        actions = tuple(
            action
            for action in context.analyzer.play_actions()
            if isinstance(action, PlayCardAction) and action.card.metadata.is_stadium()
        )
        if not actions:
            return self._result(
                passed=False,
                action=None,
                reason="No stadium action available.",
                metadata={"available_stadium_actions": 0},
                execution_time=perf_counter() - start,
            )
        return self._result(
            passed=True,
            action=actions[0],
            reason="Stadium play is available.",
            metadata={"available_stadium_actions": len(actions)},
            execution_time=perf_counter() - start,
        )
