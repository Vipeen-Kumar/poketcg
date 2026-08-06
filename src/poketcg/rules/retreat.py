"""Retreat rule."""

from __future__ import annotations

from time import perf_counter

from poketcg.actions import RetreatAction

from poketcg.decision.context import DecisionContext
from poketcg.decision.results import RuleResult

from .base import BaseRule
from .strategy import pokemon_board_value


class RetreatRule(BaseRule):
    """Select a legal retreat action when a bench Pokemon offers a better position."""

    rule_name = "RetreatRule"
    description = "Choose the retreat that improves the active board position."
    default_priority = 700

    def applies(self, context: DecisionContext) -> bool:
        active = context.analyzer.active()
        if active is None:
            return False
        return any(self._action_is_improving(context, action) for action in context.analyzer.retreat_actions())

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

        improving_actions = [action for action in actions if self._action_is_improving(context, action)]
        if not improving_actions:
            return self._result(
                passed=False,
                action=None,
                reason="No retreat target improves the current board position.",
                metadata={"available_retreat_actions": len(actions)},
                execution_time=perf_counter() - start,
            )

        active = context.analyzer.active()
        active_score = pokemon_board_value(active)
        selected = max(
            improving_actions,
            key=lambda action: (
                self._retreat_gain(action),
                pokemon_board_value(action.target_pokemon),
                -action.action_index,
            ),
        )
        target = selected.target_pokemon
        target_name = target.name if target is not None else "unknown Pokemon"
        return self._result(
            passed=True,
            action=selected,
            reason=f"Retreat to {target_name} for a stronger immediate position.",
            metadata={
                "available_retreat_actions": len(actions),
                "active_score": active_score,
                "target_score": pokemon_board_value(target),
            },
            execution_time=perf_counter() - start,
        )

    def _action_is_improving(self, context: DecisionContext, action: RetreatAction) -> bool:
        active = context.analyzer.active()
        target = action.target_pokemon
        if active is None or target is None:
            return False
        return pokemon_board_value(target) > pokemon_board_value(active)

    def _retreat_gain(self, action: RetreatAction) -> tuple[int, int, int]:
        active = action.target_pokemon
        return pokemon_board_value(active)
