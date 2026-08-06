"""Typed action dataclasses."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from poketcg.cards.models import AbilityData, AttackData
from poketcg.domain import Card, GameState, Observation, OptionReference, PlayerSide, Pokemon, SelectContext, SelectType, StatusCondition, Zone

from .enums import ActionKind


@dataclass(slots=True, kw_only=True)
class BaseAction:
    selected_indices: tuple[int, ...]
    kind: ActionKind
    option: OptionReference
    selection_context: SelectContext
    selection_type: SelectType
    metadata: dict[str, object] = field(default_factory=dict)
    
    @property
    def action_index(self) -> int:
        """Backward compatibility property. Returns first selected index."""
        return self.selected_indices[0] if self.selected_indices else -1


@dataclass(slots=True, kw_only=True)
class EndTurnAction(BaseAction):
    pass


@dataclass(slots=True, kw_only=True)
class PlayCardAction(BaseAction):
    card: Card
    source_zone: Zone | None = None
    source_index: int | None = None


@dataclass(slots=True, kw_only=True)
class AttachEnergyAction(BaseAction):
    card: Card | None = None
    source_zone: Zone | None = None
    source_index: int | None = None
    target_zone: Zone | None = None
    target_index: int | None = None
    target_owner: PlayerSide | None = None
    target_pokemon: Pokemon | None = None


@dataclass(slots=True, kw_only=True)
class EvolutionAction(BaseAction):
    evolution_card: Card | None = None
    target_zone: Zone | None = None
    target_index: int | None = None
    target_owner: PlayerSide | None = None
    target_pokemon: Pokemon | None = None


@dataclass(slots=True, kw_only=True)
class AbilityAction(BaseAction):
    source_card: Card | None = None
    source_pokemon: Pokemon | None = None
    ability_name: str | None = None
    ability: AbilityData | None = None


@dataclass(slots=True, kw_only=True)
class RetreatAction(BaseAction):
    target_zone: Zone | None = None
    target_index: int | None = None
    target_owner: PlayerSide | None = None
    target_pokemon: Pokemon | None = None


@dataclass(slots=True, kw_only=True)
class AttackAction(BaseAction):
    attacker: Pokemon | None = None
    attack_id: int | None = None
    attack_name: str | None = None
    attack: AttackData | None = None
    energy_cost: tuple = ()
    damage: str | None = None
    target_pokemon: Pokemon | None = None


@dataclass(slots=True, kw_only=True)
class ChoiceAction(BaseAction):
    chosen_card: Card | None = None
    chosen_zone: Zone | None = None
    chosen_index: int | None = None
    chosen_owner: PlayerSide | None = None
    chosen_number: int | None = None
    chosen_energy_count: int | None = None
    chosen_status_condition: StatusCondition | None = None


@dataclass(slots=True, kw_only=True)
class CardChoiceAction(ChoiceAction):
    pass


@dataclass(slots=True, kw_only=True)
class EnergyChoiceAction(ChoiceAction):
    pass


@dataclass(slots=True, kw_only=True)
class SpecialConditionChoiceAction(ChoiceAction):
    pass


@dataclass(slots=True, kw_only=True)
class UnknownAction(BaseAction):
    reason: str | None = None


@dataclass(slots=True, kw_only=True)
class ActionBatch:
    state: GameState | None
    selection_context: SelectContext
    selection_type: SelectType
    actions: tuple[BaseAction, ...]

    @classmethod
    def from_observation(cls, observation: Observation, actions: Sequence[BaseAction]) -> "ActionBatch":
        if observation.selection is None:
            raise ValueError("Observation has no selection to convert into an ActionBatch.")
        return cls(
            state=observation.state,
            selection_context=observation.selection.context,
            selection_type=observation.selection.selection_type,
            actions=tuple(actions),
        )
