"""Typed domain dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from .enums import (
    ActionType,
    CardType,
    GamePhase,
    OptionType,
    PlayerSide,
    PokemonType,
    SelectContext,
    Stage,
    StatusCondition,
    Zone,
)


@dataclass(slots=True)
class Ability:
    name: str
    text: str
    source_card_id: int | None = None


@dataclass(slots=True)
class Attack:
    attack_id: int
    name: str
    text: str
    damage: int | None = None
    energy_cost: tuple[PokemonType, ...] = ()


@dataclass(slots=True)
class Card:
    card_id: int
    name: str
    card_type: CardType
    owner: PlayerSide = PlayerSide.UNKNOWN
    serial: int | None = None
    pokemon_type: PokemonType | None = None
    stage: Stage | None = None
    hp: int | None = None
    retreat_cost: int | None = None
    weakness: PokemonType | None = None
    resistance: PokemonType | None = None
    evolves_from: str | None = None
    is_ex: bool = False
    is_mega_ex: bool = False
    is_tera: bool = False
    is_ace_spec: bool = False
    abilities: tuple[Ability, ...] = ()
    attacks: tuple[Attack, ...] = ()


@dataclass(slots=True)
class Pokemon:
    card: Card
    current_hp: int
    max_hp: int
    appeared_this_turn: bool = False
    attached_energy_types: tuple[PokemonType, ...] = ()
    attached_energy_cards: tuple[Card, ...] = ()
    attached_tools: tuple[Card, ...] = ()
    pre_evolutions: tuple[Card, ...] = ()
    special_conditions: tuple[StatusCondition, ...] = ()


@dataclass(slots=True)
class Deck:
    card_ids: tuple[int, ...]
    name: str | None = None


@dataclass(slots=True)
class Bench:
    pokemon: tuple[Pokemon, ...] = ()
    max_size: int = 5


@dataclass(slots=True)
class PrizeCards:
    cards: tuple[Card | None, ...] = ()


@dataclass(slots=True)
class Player:
    side: PlayerSide
    active: Pokemon | None = None
    bench: Bench = field(default_factory=Bench)
    hand: tuple[Card, ...] | None = None
    hand_count: int = 0
    deck_count: int = 0
    discard: tuple[Card, ...] = ()
    prizes: PrizeCards = field(default_factory=PrizeCards)
    status_conditions: tuple[StatusCondition, ...] = ()


@dataclass(slots=True)
class GameLogEntry:
    event_name: str
    player: PlayerSide | None = None
    card_id: int | None = None
    serial: int | None = None
    source_zone: Zone | None = None
    target_zone: Zone | None = None
    target_card_id: int | None = None
    attack_id: int | None = None
    value: int | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class GameState:
    turn: int = 0
    turn_action_count: int = 0
    phase: GamePhase = GamePhase.UNKNOWN
    current_player: PlayerSide = PlayerSide.UNKNOWN
    first_player: PlayerSide = PlayerSide.UNKNOWN
    supporter_played: bool = False
    stadium_played: bool = False
    energy_attached: bool = False
    retreated: bool = False
    result: PlayerSide | None = None
    players: tuple[Player, ...] = ()
    stadium: Card | None = None
    looking: tuple[Card | None, ...] | None = None


@dataclass(slots=True)
class OptionReference:
    option_type: OptionType
    zone: Zone | None = None
    zone_index: int | None = None
    owner: PlayerSide | None = None
    tool_index: int | None = None
    energy_index: int | None = None
    energy_count: int | None = None
    in_play_zone: Zone | None = None
    in_play_index: int | None = None
    attack_id: int | None = None
    card_id: int | None = None
    serial: int | None = None
    number: int | None = None
    special_condition: StatusCondition | None = None


@dataclass(slots=True)
class EffectContext:
    source_card: Card | None = None
    context_card: Card | None = None
    exposed_deck_cards: tuple[Card, ...] | None = None
    remaining_damage_counters: int = 0
    remaining_energy_cost: int = 0


@dataclass(slots=True)
class SelectPrompt:
    context: SelectContext
    min_count: int
    max_count: int
    options: tuple[OptionReference, ...]
    effect_context: EffectContext = field(default_factory=EffectContext)


@dataclass(slots=True)
class LegalAction:
    action_type: ActionType
    option_index: int
    option: OptionReference


@dataclass(slots=True)
class ActionSelection:
    selected_option_indices: tuple[int, ...]


@dataclass(slots=True)
class Observation:
    state: GameState | None
    logs: tuple[GameLogEntry, ...]
    selection: SelectPrompt | None
    raw_search_input: str | None = None
    raw_payload: Mapping[str, object] | None = None


@dataclass(slots=True)
class EvaluationBatch:
    observations: Sequence[Observation] = ()
    legal_actions: Sequence[Sequence[LegalAction]] = ()
