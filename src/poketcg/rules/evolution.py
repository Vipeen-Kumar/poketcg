"""Evolution rule."""

from __future__ import annotations

from time import perf_counter

from poketcg.actions import EvolutionAction

from poketcg.decision.context import DecisionContext
from poketcg.decision.results import RuleResult

from .base import BaseRule
from .strategy import evolution_board_value


class EvolutionRule(BaseRule):
    """Select an evolution that improves survivability or attack ceiling."""

    rule_name = "EvolutionRule"
    description = "Choose the evolution that improves HP or attack potential the most."
    default_priority = 900

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

        improving_actions = [action for action in actions if max(evolution_board_value(action.target_pokemon, action.evolution_card)[:2]) > 0]
        if not improving_actions:
            return self._result(
                passed=False,
                action=None,
                reason="No evolution meaningfully improves the board.",
                metadata={"available_evolution_actions": len(actions)},
                execution_time=perf_counter() - start,
            )

        selected = max(
            improving_actions,
            key=lambda action: (
                evolution_board_value(action.target_pokemon, action.evolution_card)[0],
                evolution_board_value(action.target_pokemon, action.evolution_card)[1],
                evolution_board_value(action.target_pokemon, action.evolution_card)[2],
                -action.action_index,
            ),
        )
        hp_gain, attack_gain, current_energy = evolution_board_value(selected.target_pokemon, selected.evolution_card)
        target_name = selected.target_pokemon.name if selected.target_pokemon is not None else "unknown Pokemon"
        return self._result(
            passed=True,
            action=selected,
            reason=f"Evolution improves {target_name} by +{hp_gain} HP and +{attack_gain} attack power.",
            metadata={
                "available_evolution_actions": len(actions),
                "hp_gain": hp_gain,
                "attack_gain": attack_gain,
                "current_energy": current_energy,
            },
            execution_time=perf_counter() - start,
        )
