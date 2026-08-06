"""Winning attack rule."""

from __future__ import annotations

from time import perf_counter

from poketcg.actions import AttackAction
from poketcg.domain import PlayerSide

from poketcg.decision.context import DecisionContext
from poketcg.decision.results import RuleResult

from .base import BaseRule
from .strategy import attack_is_lethal, attack_priority_score


class WinningAttackRule(BaseRule):
    """Select a lethal attack when it takes the final prize cards."""

    rule_name = "WinningAttackRule"
    description = "Choose a lethal attack when the opponent is on their last Prize card."
    default_priority = 1200

    def applies(self, context: DecisionContext) -> bool:
        opponent_prizes = context.analyzer.prizes_remaining(PlayerSide.OPPONENT)
        if opponent_prizes > 1:
            return False
        opponent = context.analyzer.opponent()
        opponent_hp = 0 if opponent is None or opponent.active is None else opponent.active.current_hp
        return any(attack_is_lethal(action, opponent_hp) for action in context.analyzer.attack_actions())

    def evaluate(self, context: DecisionContext) -> RuleResult:
        start = perf_counter()
        opponent = context.analyzer.opponent()
        opponent_hp = 0 if opponent is None or opponent.active is None else opponent.active.current_hp
        opponent_prizes = context.analyzer.prizes_remaining(PlayerSide.OPPONENT)
        actions = tuple(action for action in context.analyzer.attack_actions() if isinstance(action, AttackAction))
        lethal_actions = tuple(action for action in actions if attack_is_lethal(action, opponent_hp))
        if not lethal_actions:
            return self._result(
                passed=False,
                action=None,
                reason="No winning attack is available.",
                metadata={"opponent_hp": opponent_hp, "opponent_prizes_remaining": opponent_prizes},
                execution_time=perf_counter() - start,
            )

        selected = max(lethal_actions, key=lambda action: attack_priority_score(action, opponent_hp))
        damage = selected.damage or "0"
        return self._result(
            passed=True,
            action=selected,
            reason=f"Attack deals {damage} damage and takes the final Prize cards.",
            metadata={
                "opponent_hp": opponent_hp,
                "opponent_prizes_remaining": opponent_prizes,
                "lethal_actions": len(lethal_actions),
            },
            execution_time=perf_counter() - start,
        )
