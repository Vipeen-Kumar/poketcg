"""Energy attachment rule."""

from __future__ import annotations

from time import perf_counter

from poketcg.actions import AttachEnergyAction

from poketcg.decision.context import DecisionContext
from poketcg.decision.results import RuleResult

from .base import BaseRule


class AttachEnergyRule(BaseRule):
    """Select a legal energy attachment when one is still available."""

    rule_name = "AttachEnergyRule"
    description = "Choose the first legal energy attachment action."
    default_priority = 700

    def applies(self, context: DecisionContext) -> bool:
        return not context.observation.energy_attached and any(isinstance(action, AttachEnergyAction) for action in context.analyzer.energy_actions())

    def evaluate(self, context: DecisionContext) -> RuleResult:
        start = perf_counter()
        actions = tuple(action for action in context.analyzer.energy_actions() if isinstance(action, AttachEnergyAction))
        if not actions:
            return self._result(
                passed=False,
                action=None,
                reason="No attachable energy.",
                metadata={"available_energy_actions": 0},
                execution_time=perf_counter() - start,
            )
        return self._result(
            passed=True,
            action=actions[0],
            reason="Energy attachment is still unused.",
            metadata={"available_energy_actions": len(actions)},
            execution_time=perf_counter() - start,
        )
