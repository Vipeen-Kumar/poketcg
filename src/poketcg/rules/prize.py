"""Prize progression attack rule."""

from __future__ import annotations

from time import perf_counter

from poketcg.actions import AttackAction

from poketcg.decision.context import DecisionContext
from poketcg.decision.results import RuleResult

from .base import BaseRule
from .strategy import attack_damage_value, attack_priority_score


class PrizeRule(BaseRule):
    """Select the attack that makes the strongest immediate Prize progress."""

    rule_name = "PrizeRule"
    description = "Choose the attack that deals the most damage without already being lethal."
    default_priority = 600

    def applies(self, context: DecisionContext) -> bool:
        return any((attack_damage_value(action) or 0) > 0 for action in context.analyzer.attack_actions())

    def evaluate(self, context: DecisionContext) -> RuleResult:
        start = perf_counter()
        actions = tuple(action for action in context.analyzer.attack_actions() if isinstance(action, AttackAction))
        damaging_actions = tuple(action for action in actions if (attack_damage_value(action) or 0) > 0)
        if not damaging_actions:
            return self._result(
                passed=False,
                action=None,
                reason="No prize-progressing attack is available.",
                metadata={"damaging_attacks": 0},
                execution_time=perf_counter() - start,
            )

        selected = max(damaging_actions, key=lambda action: attack_priority_score(action, 999999))
        damage = attack_damage_value(selected) or 0
        return self._result(
            passed=True,
            action=selected,
            reason=f"Attack advances Prize progress with {damage} damage.",
            metadata={"damaging_attacks": len(damaging_actions), "damage": damage},
            execution_time=perf_counter() - start,
        )
