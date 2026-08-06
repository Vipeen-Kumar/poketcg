"""Knockout attack rule."""

from __future__ import annotations

from time import perf_counter

from poketcg.actions import AttackAction

from poketcg.decision.context import DecisionContext
from poketcg.decision.results import RuleResult

from .base import BaseRule
from .strategy import attack_is_lethal, attack_overkill, attack_priority_score


class KnockoutRule(BaseRule):
    """Select a lethal attack that Knocks Out the opponent Active Pokemon."""

    rule_name = "KnockoutRule"
    description = "Choose the attack that best Knocks Out the opposing Active Pokemon."
    default_priority = 1100

    def applies(self, context: DecisionContext) -> bool:
        opponent = context.analyzer.opponent()
        opponent_hp = 0 if opponent is None or opponent.active is None else opponent.active.current_hp
        return any(attack_is_lethal(action, opponent_hp) for action in context.analyzer.attack_actions())

    def evaluate(self, context: DecisionContext) -> RuleResult:
        start = perf_counter()
        opponent = context.analyzer.opponent()
        opponent_hp = 0 if opponent is None or opponent.active is None else opponent.active.current_hp
        actions = tuple(action for action in context.analyzer.attack_actions() if isinstance(action, AttackAction))
        lethal_actions = tuple(action for action in actions if attack_is_lethal(action, opponent_hp))
        if not lethal_actions:
            return self._result(
                passed=False,
                action=None,
                reason="No knockout attack is available.",
                metadata={"opponent_hp": opponent_hp, "lethal_actions": 0},
                execution_time=perf_counter() - start,
            )

        selected = min(
            lethal_actions,
            key=lambda action: (
                attack_overkill(action, opponent_hp) or 9999,
                -attack_priority_score(action, opponent_hp)[1],
                -attack_priority_score(action, opponent_hp)[3],
                action.action_index,
            ),
        )
        damage = selected.damage or "0"
        overkill = attack_overkill(selected, opponent_hp) or 0
        return self._result(
            passed=True,
            action=selected,
            reason=f"Attack deals {damage} damage and scores a Knock Out.",
            metadata={
                "opponent_hp": opponent_hp,
                "lethal_actions": len(lethal_actions),
                "overkill": overkill,
            },
            execution_time=perf_counter() - start,
        )
