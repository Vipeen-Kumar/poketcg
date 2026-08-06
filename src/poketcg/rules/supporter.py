"""Supporter rule."""

from __future__ import annotations

from time import perf_counter

from poketcg.actions import PlayCardAction

from poketcg.decision.context import DecisionContext
from poketcg.decision.results import RuleResult

from .base import BaseRule
from .strategy import supporter_is_beneficial, supporter_score


class SupporterRule(BaseRule):
    """Select a legal Supporter play when one is available."""

    rule_name = "SupporterRule"
    description = "Choose a beneficial legal supporter play action."
    default_priority = 800

    def applies(self, context: DecisionContext) -> bool:
        state = context.observation.state
        if state is None or state.supporter_played:
            return False
        return any(
            isinstance(action, PlayCardAction)
            and action.card.metadata.is_supporter()
            and supporter_is_beneficial(action.card)
            for action in context.analyzer.play_actions()
        )

    def evaluate(self, context: DecisionContext) -> RuleResult:
        start = perf_counter()
        actions = tuple(
            action
            for action in context.analyzer.play_actions()
            if isinstance(action, PlayCardAction) and action.card.metadata.is_supporter() and supporter_is_beneficial(action.card)
        )
        if not actions:
            return self._result(
                passed=False,
                action=None,
                reason="No supporter action available.",
                metadata={"available_supporter_actions": 0},
                execution_time=perf_counter() - start,
            )
        selected = sorted(actions, key=lambda action: (-supporter_score(action.card)[0], -supporter_score(action.card)[1], action.action_index))[0]
        score = supporter_score(selected.card)
        return self._result(
            passed=True,
            action=selected,
            reason=f"Supporter {selected.card.name} looks beneficial.",
            metadata={"available_supporter_actions": len(actions), "supporter_score": score[0]},
            execution_time=perf_counter() - start,
        )
