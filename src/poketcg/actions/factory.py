"""Factory converting parsed legal options into typed actions."""

from __future__ import annotations

from collections.abc import Sequence
from itertools import combinations

from poketcg.cards.models import AbilityData, AttackData
from poketcg.domain import (
    Card,
    GameState,
    Observation,
    OptionReference,
    OptionType,
    Player,
    PlayerSide,
    Pokemon,
    SelectPrompt,
    Zone,
)

from .enums import ActionKind
from .exceptions import ActionValidationError, CorruptedActionError
from .models import (
    AbilityAction,
    ActionBatch,
    AttackAction,
    AttachEnergyAction,
    BaseAction,
    CardChoiceAction,
    ChoiceAction,
    EndTurnAction,
    EnergyChoiceAction,
    EvolutionAction,
    PlayCardAction,
    RetreatAction,
    SpecialConditionChoiceAction,
    UnknownAction,
)


class ActionFactory:
    """Convert parsed selections into strongly typed actions."""

    def from_observation(self, observation: Observation) -> ActionBatch:
        """Build an action batch from a parsed observation."""

        if observation.selection is None:
            raise CorruptedActionError("Observation has no legal selection to convert.")
        actions = self.from_selection(observation.selection, state=observation.state)
        return ActionBatch.from_observation(observation, actions)

    def from_selection(self, selection: SelectPrompt, *, state: GameState | None = None) -> tuple[BaseAction, ...]:
        """Build typed actions from a parsed selection prompt."""

        # Check if this is a multi-select context (minCount > 1)
        if selection.min_count > 1:
            return self._build_combination_actions(selection, state=state)
        
        # Single-selection: existing behavior
        attack_metadata_queue = self._attack_metadata_queue(selection, state)
        actions: list[BaseAction] = []
        
        for option_index, option in enumerate(selection.options):
            attack_metadata = attack_metadata_queue.pop(0) if option.option_type is OptionType.ATTACK and attack_metadata_queue else None
            actions.append(self._build_action(option_index, selection, option, state=state, attack_metadata=attack_metadata))
        return tuple(actions)

    def _build_combination_actions(self, selection: SelectPrompt, *, state: GameState | None = None) -> tuple[BaseAction, ...]:
        """Build all valid combination actions for multi-select contexts.
        
        Generates all combinations from min_count to max_count indices.
        Each combination is represented as a single BaseAction with multiple selected_indices.
        """
        actions: list[BaseAction] = []
        option_indices = list(range(len(selection.options)))
        
        # Generate all combinations of required sizes
        for combo_size in range(selection.min_count, selection.max_count + 1):
            for combo_indices in combinations(option_indices, combo_size):
                # Build action for this combination
                action = self._build_combination_action(combo_indices, selection, state=state)
                actions.append(action)
        
        return tuple(actions)

    def _build_combination_action(
        self,
        combo_indices: tuple[int, ...],
        selection: SelectPrompt,
        *,
        state: GameState | None = None,
    ) -> BaseAction:
        """Build a single action representing a combination of selected indices."""
        import sys
        # Get first option for metadata (represents primary selection)
        first_option = selection.options[combo_indices[0]]
        
        # Common fields for all combination actions
        base_kwargs = {
            "selected_indices": combo_indices,
            "option": first_option,
            "selection_context": selection.context,
            "selection_type": selection.selection_type,
            "metadata": dict(first_option.metadata),
        }
        
        # Determine action type based on first option
        # For multi-card selections, use CardChoiceAction
        if first_option.option_type in {OptionType.CARD, OptionType.TOOL_CARD, OptionType.ENERGY_CARD, OptionType.DISCARD, OptionType.SKILL}:
            action = CardChoiceAction(
                kind=ActionKind.CHOOSE_CARD,
                chosen_card=first_option.card,
                chosen_zone=first_option.zone,
                chosen_index=first_option.zone_index,
                chosen_owner=first_option.owner,
                **base_kwargs,
            )
            print(f"[TRACE-FACTORY] Created CardChoiceAction combo={combo_indices} id={id(action)} selected_indices={action.selected_indices}", file=sys.stderr)
            return action
        
        # For other option types, use generic ChoiceAction
        action = ChoiceAction(
            kind=ActionKind.CHOOSE_CARD,
            chosen_card=first_option.card,
            chosen_zone=first_option.zone,
            chosen_index=first_option.zone_index,
            chosen_owner=first_option.owner,
            **base_kwargs,
        )
        print(f"[TRACE-FACTORY] Created ChoiceAction combo={combo_indices} id={id(action)} selected_indices={action.selected_indices}", file=sys.stderr)
        return action

    def _build_action(
        self,
        option_index: int,
        selection: SelectPrompt,
        option: OptionReference,
        *,
        state: GameState | None,
        attack_metadata: AttackData | None,
    ) -> BaseAction:
        base_kwargs = {
            "selected_indices": (option_index,),
            "option": option,
            "selection_context": selection.context,
            "selection_type": selection.selection_type,
            "metadata": dict(option.metadata),
        }

        if option.option_type is OptionType.END:
            return EndTurnAction(kind=ActionKind.END_TURN, **base_kwargs)

        if option.option_type is OptionType.PLAY:
            card = self._require_card(option, option_index=option_index, expected="PLAY")
            return PlayCardAction(
                kind=ActionKind.PLAY_CARD,
                card=card,
                source_zone=option.zone,
                source_index=option.zone_index,
                **base_kwargs,
            )

        if option.option_type is OptionType.ATTACH:
            return AttachEnergyAction(
                kind=ActionKind.ATTACH_ENERGY,
                card=option.card,
                source_zone=option.zone,
                source_index=option.zone_index,
                target_zone=option.in_play_zone,
                target_index=option.in_play_index,
                target_owner=option.owner,
                target_pokemon=self._resolve_target_pokemon(state, option),
                **base_kwargs,
            )

        if option.option_type is OptionType.EVOLVE:
            return EvolutionAction(
                kind=ActionKind.EVOLVE,
                evolution_card=option.card,
                target_zone=option.in_play_zone,
                target_index=option.in_play_index,
                target_owner=option.owner,
                target_pokemon=self._resolve_target_pokemon(state, option),
                **base_kwargs,
            )

        if option.option_type is OptionType.ABILITY:
            source_pokemon = self._resolve_target_pokemon(state, option)
            ability = self._resolve_ability_metadata(source_pokemon, option_index)
            return AbilityAction(
                kind=ActionKind.USE_ABILITY,
                source_card=option.card,
                source_pokemon=source_pokemon,
                ability_name=None if ability is None else ability.name,
                ability=ability,
                **base_kwargs,
            )

        if option.option_type is OptionType.RETREAT:
            return RetreatAction(
                kind=ActionKind.RETREAT,
                target_zone=option.in_play_zone or option.zone,
                target_index=option.in_play_index if option.in_play_index is not None else option.zone_index,
                target_owner=option.owner,
                target_pokemon=self._resolve_target_pokemon(state, option),
                **base_kwargs,
            )

        if option.option_type is OptionType.ATTACK:
            attacker = state.me.active if state is not None and state.me.active is not None else None
            return AttackAction(
                kind=ActionKind.ATTACK,
                attacker=attacker,
                attack_id=option.attack_id,
                attack_name=None if attack_metadata is None else attack_metadata.name,
                attack=attack_metadata,
                energy_cost=() if attack_metadata is None else attack_metadata.cost.symbols,
                damage=None if attack_metadata is None else attack_metadata.damage,
                target_pokemon=self._resolve_target_pokemon(state, option),
                **base_kwargs,
            )

        if option.option_type in {OptionType.CARD, OptionType.TOOL_CARD, OptionType.ENERGY_CARD, OptionType.DISCARD, OptionType.SKILL}:
            kind = ActionKind.CHOOSE_SKILL if option.option_type is OptionType.SKILL else ActionKind.CHOOSE_CARD
            action_cls = ChoiceAction if option.option_type is OptionType.SKILL else CardChoiceAction
            return action_cls(
                kind=kind,
                chosen_card=option.card,
                chosen_zone=option.zone,
                chosen_index=option.zone_index,
                chosen_owner=option.owner,
                **base_kwargs,
            )

        if option.option_type is OptionType.ENERGY:
            return EnergyChoiceAction(
                kind=ActionKind.CHOOSE_ENERGY,
                chosen_card=option.card,
                chosen_zone=option.zone,
                chosen_index=option.zone_index,
                chosen_owner=option.owner,
                chosen_energy_count=option.energy_count,
                **base_kwargs,
            )

        if option.option_type is OptionType.NUMBER:
            return ChoiceAction(
                kind=ActionKind.CHOOSE_NUMBER,
                chosen_number=option.number,
                **base_kwargs,
            )

        if option.option_type in {OptionType.YES, OptionType.NO}:
            return ChoiceAction(
                kind=ActionKind.CHOOSE_BOOLEAN,
                chosen_number=1 if option.option_type is OptionType.YES else 0,
                **base_kwargs,
            )

        if option.option_type is OptionType.SPECIAL_CONDITION:
            return SpecialConditionChoiceAction(
                kind=ActionKind.CHOOSE_SPECIAL_CONDITION,
                chosen_status_condition=option.special_condition,
                **base_kwargs,
            )

        return UnknownAction(
            kind=ActionKind.UNKNOWN,
            reason=f"Unhandled option type: {option.option_type.name}",
            **base_kwargs,
        )

    def _attack_metadata_queue(self, selection: SelectPrompt, state: GameState | None) -> list[AttackData]:
        if state is None or state.me.active is None:
            return []
        attack_options = [option for option in selection.options if option.option_type is OptionType.ATTACK]
        attacks = list(state.me.active.card.metadata.attacks)
        if len(attack_options) == len(attacks):
            return attacks
        if len(attacks) == 1 and attack_options:
            return attacks * len(attack_options)
        return []

    def _resolve_ability_metadata(self, pokemon: Pokemon | None, option_index: int) -> AbilityData | None:
        if pokemon is None:
            return None
        abilities = tuple(ability for ability in pokemon.card.metadata.abilities if ability.kind == "ability")
        if len(abilities) == 1:
            return abilities[0]
        if 0 <= option_index < len(abilities):
            return abilities[option_index]
        return None

    def _resolve_target_pokemon(self, state: GameState | None, option: OptionReference) -> Pokemon | None:
        if state is None:
            return None
        zone = option.in_play_zone or option.zone
        zone_index = option.in_play_index if option.in_play_index is not None else option.zone_index
        owner = option.owner if option.owner is not None else PlayerSide.SELF
        player = self._player_from_side(state, owner)
        if player is None or zone is None:
            return None
        if zone is Zone.ACTIVE:
            return player.active
        if zone is Zone.BENCH and zone_index is not None and 0 <= zone_index < len(player.bench.pokemon):
            return player.bench.pokemon[zone_index]
        return None

    def _player_from_side(self, state: GameState, side: PlayerSide) -> Player | None:
        if side is PlayerSide.SELF:
            return state.me
        if side is PlayerSide.OPPONENT:
            return state.opponent
        return None

    def _require_card(self, option: OptionReference, *, option_index: int, expected: str) -> Card:
        if option.card is None:
            raise ActionValidationError(f"Option index {option_index} for {expected} is missing a required card reference.")
        return option.card
