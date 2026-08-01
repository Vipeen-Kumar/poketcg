"""Factory converting parsed legal options into typed actions."""

from __future__ import annotations

from collections.abc import Sequence

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

        attack_metadata_queue = self._attack_metadata_queue(selection, state)
        actions: list[BaseAction] = []
        for option_index, option in enumerate(selection.options):
            attack_metadata = attack_metadata_queue.pop(0) if option.option_type is OptionType.ATTACK and attack_metadata_queue else None
            actions.append(self._build_action(option_index, selection, option, state=state, attack_metadata=attack_metadata))
        return tuple(actions)

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
            "action_index": option_index,
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
