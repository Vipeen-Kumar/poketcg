"""Attack rule."""

from __future__ import annotations

from time import perf_counter

from poketcg.actions import AttackAction

from poketcg.decision.context import DecisionContext
from poketcg.decision.results import RuleResult

from .base import BaseRule
from .strategy import attack_priority_score


class AttackRule(BaseRule):
    """Select a legal attack when the active Pokemon can attack."""

    rule_name = "AttackRule"
    description = "Choose the best remaining legal attack action."
    default_priority = 500

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
        opponent = context.analyzer.opponent()
        opponent_hp = 0 if opponent is None or opponent.active is None else opponent.active.current_hp
        selected = max(actions, key=lambda action: attack_priority_score(action, opponent_hp))
        damage = selected.damage or "0"
        return self._result(
            passed=True,
            action=selected,
            reason=f"Attack deals {damage} damage as the best remaining attack.",
            metadata={"available_attacks": len(actions), "opponent_hp": opponent_hp},
            execution_time=perf_counter() - start,
        )
