"""Evolution rule."""

from __future__ import annotations

from time import perf_counter

from poketcg.actions import EvolutionAction

from poketcg.decision.context import DecisionContext
from poketcg.decision.results import RuleResult

from .base import BaseRule


class EvolutionRule(BaseRule):
    """Select a legal evolution action when one exists."""

    rule_name = "EvolutionRule"
    description = "Choose the first legal evolution action."
    default_priority = 800

    def applies(self, context: DecisionContext) -> bool:
        return context.analyzer.can_evolve() and bool(context.analyzer.evolution_actions())

    def evaluate(self, context: DecisionContext) -> RuleResult:
        start = perf_counter()
        actions = tuple(action for action in context.analyzer.evolution_actions() if isinstance(action, EvolutionAction))
        if not actions:
            return self._result(
                passed=False,
                action=None,
                reason="No evolution action available.",
                metadata={"available_evolution_actions": 0},
                execution_time=perf_counter() - start,
            )
        return self._result(
            passed=True,
            action=actions[0],
            reason="Evolution action is available.",
            metadata={"available_evolution_actions": len(actions)},
            execution_time=perf_counter() - start,
        )
