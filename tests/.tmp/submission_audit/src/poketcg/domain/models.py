"""Typed domain dataclasses."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .enums import (
    ActionType,
    CardType,
    GamePhase,
    LogType,
    OptionType,
    PlayerSide,
    PokemonType,
    SelectContext,
    SelectType,
    Stage,
    StatusCondition,
    Zone,
)

if TYPE_CHECKING:
    from poketcg.cards.models import CardData


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
    metadata: CardData
    owner: PlayerSide = PlayerSide.UNKNOWN
    serial: int | None = None
    player_index: int | None = None

    @property
    def card_id(self) -> int:
        return self.metadata.card_id

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def card_type(self) -> CardType:
        return self.metadata.card_type

    @property
    def pokemon_type(self) -> PokemonType | None:
        return self.metadata.pokemon_type

    @property
    def stage(self) -> Stage | None:
        return self.metadata.stage

    @property
    def hp(self) -> int | None:
        return self.metadata.hp

    @property
    def retreat_cost(self) -> int | None:
        if self.metadata.retreat_cost is None:
            return None
        return self.metadata.retreat_cost.colorless

    @property
    def weakness(self) -> PokemonType | None:
        if self.metadata.weakness is None:
            return None
        return self.metadata.weakness.pokemon_type

    @property
    def resistance(self) -> PokemonType | None:
        if self.metadata.resistance is None:
            return None
        return self.metadata.resistance.pokemon_type

    @property
    def evolves_from(self) -> str | None:
        return self.metadata.evolution.evolves_from

    @property
    def is_ex(self) -> bool:
        return self.metadata.is_ex()

    @property
    def is_mega_ex(self) -> bool:
        return self.metadata.is_mega_ex()

    @property
    def is_tera(self) -> bool:
        return self.metadata.is_tera()

    @property
    def is_ace_spec(self) -> bool:
        return self.metadata.rule == "ACE SPEC"


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

    @property
    def serial(self) -> int | None:
        return self.card.serial

    @property
    def card_id(self) -> int:
        return self.card.card_id

    @property
    def name(self) -> str:
        return self.card.name


@dataclass(slots=True)
class Deck:
    card_ids: tuple[int, ...]
    name: str | None = None


@dataclass(slots=True)
class Bench:
    pokemon: tuple[Pokemon | None, ...] = ()
    max_size: int = 5

    def __iter__(self):
        return iter(self.pokemon)

    def __len__(self) -> int:
        return len(self.pokemon)


@dataclass(slots=True)
class PrizeCards:
    cards: tuple[Card | None, ...] = ()

    @property
    def remaining(self) -> int:
        return len(self.cards)


@dataclass(slots=True)
class Player:
    player_index: int
    side: PlayerSide
    active: Pokemon | None = None
    bench: Bench = field(default_factory=Bench)
    hand: tuple[Card, ...] | None = None
    hand_count: int = 0
    deck_count: int = 0
    discard: tuple[Card, ...] = ()
    prizes: PrizeCards = field(default_factory=PrizeCards)
    status_conditions: tuple[StatusCondition, ...] = ()

    @property
    def poisoned(self) -> bool:
        return StatusCondition.POISONED in self.status_conditions

    @property
    def burned(self) -> bool:
        return StatusCondition.BURNED in self.status_conditions

    @property
    def asleep(self) -> bool:
        return StatusCondition.ASLEEP in self.status_conditions

    @property
    def paralyzed(self) -> bool:
        return StatusCondition.PARALYZED in self.status_conditions

    @property
    def confused(self) -> bool:
        return StatusCondition.CONFUSED in self.status_conditions


@dataclass(slots=True)
class GameLogEntry:
    log_type: LogType
    event_name: str
    player_index: int | None = None
    player: PlayerSide | None = None
    card: Card | None = None
    target_card: Card | None = None
    before_card: Card | None = None
    after_card: Card | None = None
    active_card: Card | None = None
    bench_card: Card | None = None
    source_zone: Zone | None = None
    target_zone: Zone | None = None
    attack_id: int | None = None
    value: int | None = None
    put_damage_counter: bool | None = None
    is_recover: bool | None = None
    head: bool | None = None
    has_basic_pokemon: bool | None = None
    result_code: int | None = None
    reason_code: int | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class GameState:
    turn: int = 0
    turn_action_count: int = 0
    phase: GamePhase = GamePhase.UNKNOWN
    perspective_player_index: int = 0
    current_player: PlayerSide = PlayerSide.UNKNOWN
    first_player: PlayerSide = PlayerSide.UNKNOWN
    first_player_index: int | None = None
    supporter_played: bool = False
    stadium_played: bool = False
    energy_attached: bool = False
    retreated: bool = False
    result: PlayerSide | None = None
    result_code: int | None = None
    players: tuple[Player, ...] = ()
    stadium: Card | None = None
    looking: tuple[Card | None, ...] | None = None

    @property
    def me(self) -> Player:
        for player in self.players:
            if player.side is PlayerSide.SELF:
                return player
        raise LookupError("Parsed GameState does not contain the perspective player.")

    @property
    def opponent(self) -> Player:
        for player in self.players:
            if player.side is PlayerSide.OPPONENT:
                return player
        raise LookupError("Parsed GameState does not contain the opponent player.")

    @property
    def is_terminal(self) -> bool:
        return self.result_code is not None


@dataclass(slots=True)
class OptionReference:
    option_type: OptionType
    card: Card | None = None
    zone: Zone | None = None
    zone_index: int | None = None
    owner: PlayerSide | None = None
    player_index: int | None = None
    tool_index: int | None = None
    energy_index: int | None = None
    energy_count: int | None = None
    in_play_zone: Zone | None = None
    in_play_index: int | None = None
    attack_id: int | None = None
    number: int | None = None
    special_condition: StatusCondition | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class EffectContext:
    source_card: Card | None = None
    context_card: Card | None = None
    exposed_deck_cards: tuple[Card, ...] | None = None
    remaining_damage_counters: int = 0
    remaining_energy_cost: int = 0


@dataclass(slots=True)
class SelectPrompt:
    selection_type: SelectType
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

    @property
    def turn(self) -> int | None:
        if self.state is None:
            return None
        return self.state.turn

    @property
    def me(self) -> Player | None:
        if self.state is None:
            return None
        return self.state.me

    @property
    def opponent(self) -> Player | None:
        if self.state is None:
            return None
        return self.state.opponent

    @property
    def result(self) -> PlayerSide | None:
        if self.state is None:
            return None
        return self.state.result

    @property
    def is_terminal(self) -> bool:
        return self.state.is_terminal if self.state is not None else False

    @property
    def energy_attached(self) -> bool:
        return self.state.energy_attached if self.state is not None else False

    @property
    def supporter_played(self) -> bool:
        return self.state.supporter_played if self.state is not None else False

    @property
    def retreated(self) -> bool:
        return self.state.retreated if self.state is not None else False


@dataclass(slots=True)
class EvaluationBatch:
    observations: Sequence[Observation] = ()
    legal_actions: Sequence[Sequence[LegalAction]] = ()
