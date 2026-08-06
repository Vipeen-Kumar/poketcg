"""Energy attachment rule."""

from __future__ import annotations

from time import perf_counter

from poketcg.actions import AttachEnergyAction, EnergyChoiceAction

from poketcg.decision.context import DecisionContext
from poketcg.decision.results import RuleResult

from .base import BaseRule
from .strategy import pokemon_attack_gap


class AttachEnergyRule(BaseRule):
    """Select an energy attachment that moves a Pokemon toward attacking."""

    rule_name = "AttachEnergyRule"
    description = "Choose the energy attachment that closes the smallest attack gap."
    default_priority = 1000

    def applies(self, context: DecisionContext) -> bool:
        return not context.observation.energy_attached and any(
            isinstance(action, (AttachEnergyAction, EnergyChoiceAction))
            and getattr(action, "target_pokemon", None) is not None
            and (pokemon_attack_gap(getattr(action, "target_pokemon", None)) or 0) > 0
            for action in context.analyzer.energy_actions()
        )

    def evaluate(self, context: DecisionContext) -> RuleResult:
        start = perf_counter()
        actions = tuple(
            action
            for action in context.analyzer.energy_actions()
            if isinstance(action, (AttachEnergyAction, EnergyChoiceAction))
            and getattr(action, "target_pokemon", None) is not None
            and (pokemon_attack_gap(getattr(action, "target_pokemon", None)) or 0) > 0
        )
        if not actions:
            return self._result(
                passed=False,
                action=None,
                reason="No attachable energy that improves an attack path.",
                metadata={"available_energy_actions": 0},
                execution_time=perf_counter() - start,
            )

        selected = min(
            actions,
            key=lambda action: (
                pokemon_attack_gap(getattr(action, "target_pokemon", None)) or 999,
                0 if getattr(action, "target_zone", None) is not None and action.target_zone.name == "ACTIVE" else 1,
                -(getattr(action, "target_pokemon", None).current_hp if getattr(action, "target_pokemon", None) is not None else 0),
                action.action_index,
            ),
        )
        target_pokemon = getattr(selected, "target_pokemon", None)
        gap = pokemon_attack_gap(target_pokemon) or 0
        target_name = target_pokemon.name if target_pokemon is not None else "unknown Pokemon"
        return self._result(
            passed=True,
            action=selected,
            reason=f"Energy attachment closes the attack gap for {target_name}.",
            metadata={"available_energy_actions": len(actions), "attack_gap": gap},
            execution_time=perf_counter() - start,
        )
