"""Attack rule."""

from __future__ import annotations

from time import perf_counter

from poketcg.actions import AttackAction

from poketcg.decision.context import DecisionContext
from poketcg.decision.results import RuleResult

from .base import BaseRule


class AttackRule(BaseRule):
    """Select a legal attack when the active Pokémon can attack."""

    rule_name = "AttackRule"
    description = "Choose the first legal attack action."
    default_priority = 900

    def applies(self, context: DecisionContext) -> bool:
        return context.analyzer.can_attack() and not context.analyzer.is_asleep() and not context.analyzer.is_paralyzed()

    def evaluate(self, context: DecisionContext) -> RuleResult:
        start = perf_counter()
        actions = tuple(action for action in context.analyzer.attack_actions() if isinstance(action, AttackAction))
        if not actions:
            return self._result(
                passed=False,
                action=None,
                reason="No attack action available.",
                metadata={"available_attacks": 0},
                execution_time=perf_counter() - start,
            )
        return self._result(
            passed=True,
            action=actions[0],
            reason="Active Pokémon has enough energy.",
            metadata={"available_attacks": len(actions)},
            execution_time=perf_counter() - start,
        )
