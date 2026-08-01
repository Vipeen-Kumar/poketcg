"""Raw Kaggle/cabt observation parser."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from enum import Enum
from typing import Final

from poketcg.cards import BaseCardCatalog
from poketcg.cards.exceptions import UnknownCardLookupError
from poketcg.domain import (
    Bench,
    Card,
    EffectContext,
    GameLogEntry,
    GamePhase,
    GameState,
    LogType,
    Observation,
    OptionReference,
    OptionType,
    Player,
    PlayerSide,
    Pokemon,
    PokemonType,
    PrizeCards,
    SelectContext,
    SelectPrompt,
    SelectType,
    StatusCondition,
    Zone,
)

from .exceptions import (
    CorruptedObservationError,
    InvalidObservationEnumError,
    MissingObservationCardError,
    MissingObservationFieldError,
)
from .interfaces import BaseObservationParser


_ZONE_IDS: Final[dict[int, Zone]] = {
    1: Zone.DECK,
    2: Zone.HAND,
    3: Zone.DISCARD,
    4: Zone.ACTIVE,
    5: Zone.BENCH,
    6: Zone.PRIZE,
    7: Zone.STADIUM,
    8: Zone.ENERGY,
    9: Zone.TOOL,
    10: Zone.PRE_EVOLUTION,
    11: Zone.PLAYER,
    12: Zone.LOOKING,
}

_POKEMON_TYPE_IDS: Final[dict[int, PokemonType]] = {
    0: PokemonType.COLORLESS,
    1: PokemonType.GRASS,
    2: PokemonType.FIRE,
    3: PokemonType.WATER,
    4: PokemonType.LIGHTNING,
    5: PokemonType.PSYCHIC,
    6: PokemonType.FIGHTING,
    7: PokemonType.DARKNESS,
    8: PokemonType.METAL,
    9: PokemonType.DRAGON,
    10: PokemonType.RAINBOW,
    11: PokemonType.TEAM_ROCKET,
}

_SELECT_TYPE_IDS: Final[dict[int, SelectType]] = {
    0: SelectType.MAIN,
    1: SelectType.CARD,
    2: SelectType.ATTACHED_CARD,
    3: SelectType.CARD_OR_ATTACHED_CARD,
    4: SelectType.ENERGY,
    5: SelectType.SKILL,
    6: SelectType.ATTACK,
    7: SelectType.EVOLVE,
    8: SelectType.COUNT,
    9: SelectType.YES_NO,
    10: SelectType.SPECIAL_CONDITION,
}

_SELECT_CONTEXT_IDS: Final[dict[int, SelectContext]] = {
    0: SelectContext.MAIN,
    1: SelectContext.SETUP_ACTIVE_POKEMON,
    2: SelectContext.SETUP_BENCH_POKEMON,
    3: SelectContext.SWITCH,
    4: SelectContext.TO_ACTIVE,
    5: SelectContext.TO_BENCH,
    6: SelectContext.TO_FIELD,
    7: SelectContext.TO_HAND,
    8: SelectContext.DISCARD,
    9: SelectContext.TO_DECK,
    10: SelectContext.TO_DECK_BOTTOM,
    11: SelectContext.TO_PRIZE,
    12: SelectContext.NOT_MOVE,
    13: SelectContext.DAMAGE_COUNTER,
    14: SelectContext.DAMAGE_COUNTER_ANY,
    15: SelectContext.DAMAGE,
    16: SelectContext.REMOVE_DAMAGE_COUNTER,
    17: SelectContext.HEAL,
    18: SelectContext.EVOLVES_FROM,
    19: SelectContext.EVOLVES_TO,
    20: SelectContext.DEVOLVE,
    21: SelectContext.ATTACH_FROM,
    22: SelectContext.ATTACH_TO,
    23: SelectContext.DETACH_FROM,
    24: SelectContext.LOOK,
    25: SelectContext.EFFECT_TARGET,
    26: SelectContext.DISCARD_ENERGY_CARD,
    27: SelectContext.DISCARD_TOOL_CARD,
    28: SelectContext.SWITCH_ENERGY_CARD,
    29: SelectContext.DISCARD_CARD_OR_ATTACHED_CARD,
    30: SelectContext.DISCARD_ENERGY,
    31: SelectContext.TO_HAND_ENERGY,
    32: SelectContext.TO_DECK_ENERGY,
    33: SelectContext.SWITCH_ENERGY,
    34: SelectContext.SKILL_ORDER,
    35: SelectContext.ATTACK,
    36: SelectContext.DISABLE_ATTACK,
    37: SelectContext.EVOLVE,
    38: SelectContext.DRAW_COUNT,
    39: SelectContext.DAMAGE_COUNTER_COUNT,
    40: SelectContext.REMOVE_DAMAGE_COUNTER_COUNT,
    41: SelectContext.IS_FIRST,
    42: SelectContext.MULLIGAN,
    43: SelectContext.ACTIVATE,
    44: SelectContext.FIRST_EFFECT,
    45: SelectContext.MORE_DEVOLVE,
    46: SelectContext.COIN_HEAD,
    47: SelectContext.AFFECT_SPECIAL_CONDITION,
    48: SelectContext.RECOVER_SPECIAL_CONDITION,
}

_OPTION_TYPE_IDS: Final[dict[int, OptionType]] = {
    0: OptionType.NUMBER,
    1: OptionType.YES,
    2: OptionType.NO,
    3: OptionType.CARD,
    4: OptionType.TOOL_CARD,
    5: OptionType.ENERGY_CARD,
    6: OptionType.ENERGY,
    7: OptionType.PLAY,
    8: OptionType.ATTACH,
    9: OptionType.EVOLVE,
    10: OptionType.ABILITY,
    11: OptionType.DISCARD,
    12: OptionType.RETREAT,
    13: OptionType.ATTACK,
    14: OptionType.END,
    15: OptionType.SKILL,
    16: OptionType.SPECIAL_CONDITION,
}

_STATUS_IDS: Final[dict[int, StatusCondition]] = {
    0: StatusCondition.POISONED,
    1: StatusCondition.BURNED,
    2: StatusCondition.ASLEEP,
    3: StatusCondition.PARALYZED,
    4: StatusCondition.CONFUSED,
}

_LOG_TYPE_IDS: Final[dict[int, LogType]] = {
    0: LogType.SHUFFLE,
    1: LogType.HAS_BASIC_POKEMON,
    2: LogType.TURN_START,
    3: LogType.TURN_END,
    4: LogType.DRAW,
    5: LogType.DRAW_REVERSE,
    6: LogType.MOVE_CARD,
    7: LogType.MOVE_CARD_REVERSE,
    8: LogType.SWITCH,
    9: LogType.CHANGE,
    10: LogType.PLAY,
    11: LogType.ATTACH,
    12: LogType.EVOLVE,
    13: LogType.DEVOLVE,
    14: LogType.MOVE_ATTACHED,
    15: LogType.ATTACK,
    16: LogType.HP_CHANGE,
    17: LogType.POISONED,
    18: LogType.BURNED,
    19: LogType.ASLEEP,
    20: LogType.PARALYZED,
    21: LogType.CONFUSED,
    22: LogType.COIN,
    23: LogType.RESULT,
}

_PLAYER_STATE_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "active",
    "bench",
    "benchMax",
    "deckCount",
    "discard",
    "prize",
    "handCount",
    "hand",
    "poisoned",
    "burned",
    "asleep",
    "paralyzed",
    "confused",
)


class ObservationParser(BaseObservationParser):
    """Convert raw Kaggle/cabt observation payloads into internal typed models."""

    def __init__(self, card_database: BaseCardCatalog) -> None:
        self._card_database = card_database
        self._card_cache: dict[tuple[int, int | None, int | None], Card] = {}

    def parse(self, payload: Mapping[str, object]) -> Observation:
        """Parse a raw observation payload."""

        self._card_cache = {}
        observation_payload = self._require_mapping(payload, path="observation")
        logs_raw = self._require_list(self._require_field(observation_payload, "logs", "observation"), path="observation.logs")
        current_raw = observation_payload.get("current")
        select_raw = observation_payload.get("select")
        state = None if current_raw is None else self._parse_state(self._require_mapping(current_raw, path="observation.current"))
        logs = tuple(self._parse_log(log_entry, perspective_index=state.perspective_player_index if state is not None else None) for log_entry in logs_raw)
        selection = None
        if select_raw is not None:
            selection = self._parse_selection(
                self._require_mapping(select_raw, path="observation.select"),
                perspective_index=state.perspective_player_index if state is not None else None,
            )
        if state is not None and selection is not None and state.phase is GamePhase.UNKNOWN:
            state.phase = self._phase_from_selection(selection.context)
        return Observation(
            state=state,
            logs=logs,
            selection=selection,
            raw_search_input=self._optional_str(observation_payload.get("search_begin_input")),
            raw_payload=observation_payload,
        )

    def _parse_state(self, payload: Mapping[str, object]) -> GameState:
        your_index = self._require_int(payload, "yourIndex", "observation.current")
        players_payload = self._require_list(self._require_field(payload, "players", "observation.current"), path="observation.current.players")
        if len(players_payload) != 2:
            raise CorruptedObservationError("observation.current.players must contain exactly 2 players.")

        players = tuple(
            self._parse_player(
                self._require_mapping(player_payload, path=f"observation.current.players[{index}]"),
                player_index=index,
                perspective_index=your_index,
            )
            for index, player_payload in enumerate(players_payload)
        )
        first_player_raw = self._require_int(payload, "firstPlayer", "observation.current")
        result_raw = self._require_int(payload, "result", "observation.current")
        current_player = PlayerSide.SELF
        if result_raw != -1:
            phase = GamePhase.FINISHED
        elif self._require_int(payload, "turn", "observation.current") == 0:
            phase = GamePhase.SETUP
        else:
            phase = GamePhase.UNKNOWN

        stadium_cards = self._parse_card_list(
            self._require_list(self._require_field(payload, "stadium", "observation.current"), path="observation.current.stadium"),
            perspective_index=your_index,
            path="observation.current.stadium",
            allow_none=False,
        )
        stadium = stadium_cards[0] if stadium_cards else None
        looking_raw = payload.get("looking")
        looking = None
        if looking_raw is not None:
            looking = tuple(
                self._parse_optional_card(entry, perspective_index=your_index, path=f"observation.current.looking[{index}]")
                for index, entry in enumerate(self._require_list(looking_raw, path="observation.current.looking"))
            )

        result_side = None
        result_code = None
        if result_raw != -1:
            result_code = result_raw
            if result_raw == your_index:
                result_side = PlayerSide.SELF
            elif result_raw in (0, 1):
                result_side = PlayerSide.OPPONENT
            elif result_raw == 2:
                result_side = PlayerSide.UNKNOWN
            else:
                raise InvalidObservationEnumError(f"Unknown result code: {result_raw}")

        first_player_index = None if first_player_raw == -1 else first_player_raw
        first_player_side = PlayerSide.UNKNOWN if first_player_index is None else self._player_side(first_player_index, your_index)

        return GameState(
            turn=self._require_int(payload, "turn", "observation.current"),
            turn_action_count=self._require_int(payload, "turnActionCount", "observation.current"),
            phase=phase,
            perspective_player_index=your_index,
            current_player=current_player,
            first_player=first_player_side,
            first_player_index=first_player_index,
            supporter_played=self._require_bool(payload, "supporterPlayed", "observation.current"),
            stadium_played=self._require_bool(payload, "stadiumPlayed", "observation.current"),
            energy_attached=self._require_bool(payload, "energyAttached", "observation.current"),
            retreated=self._require_bool(payload, "retreated", "observation.current"),
            result=result_side,
            result_code=result_code,
            players=players,
            stadium=stadium,
            looking=looking,
        )

    def _phase_from_selection(self, context: SelectContext) -> GamePhase:
        if context in {SelectContext.SETUP_ACTIVE_POKEMON, SelectContext.SETUP_BENCH_POKEMON, SelectContext.IS_FIRST, SelectContext.MULLIGAN}:
            return GamePhase.SETUP
        if context is SelectContext.MAIN:
            return GamePhase.MAIN
        if context is SelectContext.ATTACK:
            return GamePhase.ATTACK
        return GamePhase.UNKNOWN

    def _parse_player(self, payload: Mapping[str, object], *, player_index: int, perspective_index: int) -> Player:
        for field_name in _PLAYER_STATE_REQUIRED_FIELDS:
            self._require_field(payload, field_name, f"observation.current.players[{player_index}]")

        active_values = self._require_list(payload["active"], path=f"observation.current.players[{player_index}].active")
        if len(active_values) > 1:
            raise CorruptedObservationError("Player active list must have length 0 or 1.")
        active = None
        if active_values:
            active = self._parse_optional_pokemon(
                active_values[0],
                player_index=player_index,
                perspective_index=perspective_index,
                path=f"observation.current.players[{player_index}].active[0]",
            )

        bench_values = self._require_list(payload["bench"], path=f"observation.current.players[{player_index}].bench")
        bench = Bench(
            pokemon=tuple(
                self._parse_optional_pokemon(
                    bench_entry,
                    player_index=player_index,
                    perspective_index=perspective_index,
                    path=f"observation.current.players[{player_index}].bench[{index}]",
                )
                for index, bench_entry in enumerate(bench_values)
            ),
            max_size=self._require_int(payload, "benchMax", f"observation.current.players[{player_index}]"),
        )

        hand_raw = payload.get("hand")
        hand = None
        if hand_raw is not None:
            hand = self._parse_card_list(
                self._require_list(hand_raw, path=f"observation.current.players[{player_index}].hand"),
                perspective_index=perspective_index,
                path=f"observation.current.players[{player_index}].hand",
                allow_none=False,
            )

        status_conditions = self._collect_status_conditions(payload, path=f"observation.current.players[{player_index}]")
        prizes = PrizeCards(
            cards=tuple(
                self._parse_optional_card(
                    prize_entry,
                    perspective_index=perspective_index,
                    path=f"observation.current.players[{player_index}].prize[{index}]",
                )
                for index, prize_entry in enumerate(
                    self._require_list(payload["prize"], path=f"observation.current.players[{player_index}].prize")
                )
            )
        )

        return Player(
            player_index=player_index,
            side=self._player_side(player_index, perspective_index),
            active=active,
            bench=bench,
            hand=hand,
            hand_count=self._require_int(payload, "handCount", f"observation.current.players[{player_index}]"),
            deck_count=self._require_int(payload, "deckCount", f"observation.current.players[{player_index}]"),
            discard=self._parse_card_list(
                self._require_list(payload["discard"], path=f"observation.current.players[{player_index}].discard"),
                perspective_index=perspective_index,
                path=f"observation.current.players[{player_index}].discard",
                allow_none=False,
            ),
            prizes=prizes,
            status_conditions=status_conditions,
        )

    def _parse_optional_pokemon(
        self,
        payload: object,
        *,
        player_index: int,
        perspective_index: int,
        path: str,
    ) -> Pokemon | None:
        if payload is None:
            return None
        return self._parse_pokemon(
            self._require_mapping(payload, path=path),
            player_index=player_index,
            perspective_index=perspective_index,
            path=path,
        )

    def _parse_pokemon(
        self,
        payload: Mapping[str, object],
        *,
        player_index: int,
        perspective_index: int,
        path: str,
    ) -> Pokemon:
        card_id = self._require_int(payload, "id", path)
        serial = self._require_int(payload, "serial", path)
        card = self._build_card(card_id=card_id, serial=serial, player_index=player_index, perspective_index=perspective_index)
        energies = tuple(
            self._parse_pokemon_type(energy_value, path=f"{path}.energies[{index}]")
            for index, energy_value in enumerate(self._require_list(self._require_field(payload, "energies", path), path=f"{path}.energies"))
        )
        return Pokemon(
            card=card,
            current_hp=self._require_int(payload, "hp", path),
            max_hp=self._require_int(payload, "maxHp", path),
            appeared_this_turn=self._require_bool(payload, "appearThisTurn", path),
            attached_energy_types=energies,
            attached_energy_cards=self._parse_card_list(
                self._require_list(self._require_field(payload, "energyCards", path), path=f"{path}.energyCards"),
                perspective_index=perspective_index,
                path=f"{path}.energyCards",
                allow_none=False,
            ),
            attached_tools=self._parse_card_list(
                self._require_list(self._require_field(payload, "tools", path), path=f"{path}.tools"),
                perspective_index=perspective_index,
                path=f"{path}.tools",
                allow_none=False,
            ),
            pre_evolutions=self._parse_card_list(
                self._require_list(self._require_field(payload, "preEvolution", path), path=f"{path}.preEvolution"),
                perspective_index=perspective_index,
                path=f"{path}.preEvolution",
                allow_none=False,
            ),
        )

    def _parse_selection(self, payload: Mapping[str, object], *, perspective_index: int | None) -> SelectPrompt:
        selection_type = self._parse_select_type(self._require_field(payload, "type", "observation.select"))
        context = self._parse_select_context(self._require_field(payload, "context", "observation.select"))
        if perspective_index is None:
            perspective_index = 0
        effect_context = EffectContext(
            source_card=self._parse_optional_card(payload.get("effect"), perspective_index=perspective_index, path="observation.select.effect"),
            context_card=self._parse_optional_card(
                payload.get("contextCard"),
                perspective_index=perspective_index,
                path="observation.select.contextCard",
            ),
            exposed_deck_cards=self._parse_deck_cards(payload.get("deck"), perspective_index=perspective_index),
            remaining_damage_counters=self._require_int(payload, "remainDamageCounter", "observation.select"),
            remaining_energy_cost=self._require_int(payload, "remainEnergyCost", "observation.select"),
        )
        options_raw = self._require_list(self._require_field(payload, "option", "observation.select"), path="observation.select.option")
        options = tuple(
            self._parse_option(
                self._require_mapping(option_payload, path=f"observation.select.option[{index}]"),
                perspective_index=perspective_index,
                path=f"observation.select.option[{index}]",
            )
            for index, option_payload in enumerate(options_raw)
        )
        return SelectPrompt(
            selection_type=selection_type,
            context=context,
            min_count=self._require_int(payload, "minCount", "observation.select"),
            max_count=self._require_int(payload, "maxCount", "observation.select"),
            options=options,
            effect_context=effect_context,
        )

    def _parse_option(self, payload: Mapping[str, object], *, perspective_index: int, path: str) -> OptionReference:
        option_type = self._parse_option_type(self._require_field(payload, "type", path))
        player_index = self._optional_int(payload.get("playerIndex"))
        card = None
        card_id = self._optional_int(payload.get("cardId"))
        if card_id is not None:
            card = self._build_card(
                card_id=card_id,
                serial=self._optional_int(payload.get("serial")),
                player_index=player_index,
                perspective_index=perspective_index,
            )
        metadata = self._remaining_fields(
            payload,
            excluded={
                "type",
                "area",
                "index",
                "playerIndex",
                "toolIndex",
                "energyIndex",
                "count",
                "inPlayArea",
                "inPlayIndex",
                "attackId",
                "cardId",
                "serial",
                "number",
                "specialConditionType",
            },
        )
        return OptionReference(
            option_type=option_type,
            card=card,
            zone=self._parse_zone_optional(payload.get("area")),
            zone_index=self._optional_int(payload.get("index")),
            owner=None if player_index is None else self._player_side(player_index, perspective_index),
            player_index=player_index,
            tool_index=self._optional_int(payload.get("toolIndex")),
            energy_index=self._optional_int(payload.get("energyIndex")),
            energy_count=self._optional_int(payload.get("count")),
            in_play_zone=self._parse_zone_optional(payload.get("inPlayArea")),
            in_play_index=self._optional_int(payload.get("inPlayIndex")),
            attack_id=self._optional_int(payload.get("attackId")),
            number=self._optional_int(payload.get("number")),
            special_condition=self._parse_status_optional(payload.get("specialConditionType")),
            metadata=metadata,
        )

    def _parse_log(self, payload: object, *, perspective_index: int | None) -> GameLogEntry:
        if perspective_index is None:
            perspective_index = 0
        mapping = self._require_mapping(payload, path="observation.logs[]")
        log_type = self._parse_log_type(self._require_field(mapping, "type", "observation.logs[]"))
        player_index = self._optional_int(mapping.get("playerIndex"))
        metadata = self._remaining_fields(
            mapping,
            excluded={
                "type",
                "playerIndex",
                "hasBasicPokemon",
                "cardId",
                "serial",
                "fromArea",
                "toArea",
                "cardIdActive",
                "serialActive",
                "cardIdBench",
                "serialBench",
                "cardIdBefore",
                "serialBefore",
                "cardIdAfter",
                "serialAfter",
                "cardIdTarget",
                "serialTarget",
                "attackId",
                "value",
                "putDamageCounter",
                "isRecover",
                "head",
                "result",
                "reason",
            },
        )
        return GameLogEntry(
            log_type=log_type,
            event_name=log_type.name,
            player_index=player_index,
            player=None if player_index is None else self._player_side(player_index, perspective_index),
            card=self._build_card_optional(
                card_id=self._optional_int(mapping.get("cardId")),
                serial=self._optional_int(mapping.get("serial")),
                player_index=player_index,
                perspective_index=perspective_index,
            ),
            target_card=self._build_card_optional(
                card_id=self._optional_int(mapping.get("cardIdTarget")),
                serial=self._optional_int(mapping.get("serialTarget")),
                player_index=player_index,
                perspective_index=perspective_index,
            ),
            before_card=self._build_card_optional(
                card_id=self._optional_int(mapping.get("cardIdBefore")),
                serial=self._optional_int(mapping.get("serialBefore")),
                player_index=player_index,
                perspective_index=perspective_index,
            ),
            after_card=self._build_card_optional(
                card_id=self._optional_int(mapping.get("cardIdAfter")),
                serial=self._optional_int(mapping.get("serialAfter")),
                player_index=player_index,
                perspective_index=perspective_index,
            ),
            active_card=self._build_card_optional(
                card_id=self._optional_int(mapping.get("cardIdActive")),
                serial=self._optional_int(mapping.get("serialActive")),
                player_index=player_index,
                perspective_index=perspective_index,
            ),
            bench_card=self._build_card_optional(
                card_id=self._optional_int(mapping.get("cardIdBench")),
                serial=self._optional_int(mapping.get("serialBench")),
                player_index=player_index,
                perspective_index=perspective_index,
            ),
            source_zone=self._parse_zone_optional(mapping.get("fromArea")),
            target_zone=self._parse_zone_optional(mapping.get("toArea")),
            attack_id=self._optional_int(mapping.get("attackId")),
            value=self._optional_int(mapping.get("value")),
            put_damage_counter=self._optional_bool(mapping.get("putDamageCounter")),
            is_recover=self._optional_bool(mapping.get("isRecover")),
            head=self._optional_bool(mapping.get("head")),
            has_basic_pokemon=self._optional_bool(mapping.get("hasBasicPokemon")),
            result_code=self._optional_int(mapping.get("result")),
            reason_code=self._optional_int(mapping.get("reason")),
            metadata=metadata,
        )

    def _parse_deck_cards(self, payload: object, *, perspective_index: int) -> tuple[Card, ...] | None:
        if payload is None:
            return None
        return self._parse_card_list(
            self._require_list(payload, path="observation.select.deck"),
            perspective_index=perspective_index,
            path="observation.select.deck",
            allow_none=False,
        )

    def _parse_card_list(
        self,
        payload: Sequence[object],
        *,
        perspective_index: int,
        path: str,
        allow_none: bool,
    ) -> tuple[Card, ...]:
        cards: list[Card] = []
        for index, entry in enumerate(payload):
            parsed = self._parse_optional_card(entry, perspective_index=perspective_index, path=f"{path}[{index}]")
            if parsed is None:
                if allow_none:
                    continue
                raise CorruptedObservationError(f"{path}[{index}] must be a card object, not null.")
            cards.append(parsed)
        return tuple(cards)

    def _parse_optional_card(self, payload: object, *, perspective_index: int, path: str) -> Card | None:
        if payload is None:
            return None
        mapping = self._require_mapping(payload, path=path)
        card_id = self._require_int(mapping, "id", path)
        serial = self._require_int(mapping, "serial", path)
        player_index = self._require_int(mapping, "playerIndex", path)
        return self._build_card(card_id=card_id, serial=serial, player_index=player_index, perspective_index=perspective_index)

    def _build_card(
        self,
        *,
        card_id: int,
        serial: int | None,
        player_index: int | None,
        perspective_index: int,
    ) -> Card:
        cache_key = (card_id, serial, player_index)
        cached = self._card_cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            metadata = self._card_database.get(card_id)
        except UnknownCardLookupError as exc:
            raise MissingObservationCardError(f"Observation referenced unknown card id: {card_id}") from exc
        owner = PlayerSide.UNKNOWN if player_index is None else self._player_side(player_index, perspective_index)
        card = Card(metadata=metadata, owner=owner, serial=serial, player_index=player_index)
        self._card_cache[cache_key] = card
        return card

    def _build_card_optional(
        self,
        *,
        card_id: int | None,
        serial: int | None,
        player_index: int | None,
        perspective_index: int,
    ) -> Card | None:
        if card_id is None:
            return None
        return self._build_card(card_id=card_id, serial=serial, player_index=player_index, perspective_index=perspective_index)

    def _collect_status_conditions(self, payload: Mapping[str, object], *, path: str) -> tuple[StatusCondition, ...]:
        conditions: list[StatusCondition] = []
        if self._require_bool(payload, "poisoned", path):
            conditions.append(StatusCondition.POISONED)
        if self._require_bool(payload, "burned", path):
            conditions.append(StatusCondition.BURNED)
        if self._require_bool(payload, "asleep", path):
            conditions.append(StatusCondition.ASLEEP)
        if self._require_bool(payload, "paralyzed", path):
            conditions.append(StatusCondition.PARALYZED)
        if self._require_bool(payload, "confused", path):
            conditions.append(StatusCondition.CONFUSED)
        return tuple(conditions)

    def _player_side(self, player_index: int, perspective_index: int) -> PlayerSide:
        if player_index == perspective_index:
            return PlayerSide.SELF
        if player_index in (0, 1):
            return PlayerSide.OPPONENT
        raise InvalidObservationEnumError(f"Invalid player index: {player_index}")

    def _parse_zone_optional(self, value: object) -> Zone | None:
        if value is None:
            return None
        return self._parse_enum(value, Zone, _ZONE_IDS, enum_name="Zone")

    def _parse_pokemon_type(self, value: object, *, path: str) -> PokemonType:
        return self._parse_enum(value, PokemonType, _POKEMON_TYPE_IDS, enum_name=f"PokemonType at {path}")

    def _parse_select_type(self, value: object) -> SelectType:
        return self._parse_enum(value, SelectType, _SELECT_TYPE_IDS, enum_name="SelectType")

    def _parse_select_context(self, value: object) -> SelectContext:
        return self._parse_enum(value, SelectContext, _SELECT_CONTEXT_IDS, enum_name="SelectContext")

    def _parse_option_type(self, value: object) -> OptionType:
        return self._parse_enum(value, OptionType, _OPTION_TYPE_IDS, enum_name="OptionType")

    def _parse_status_optional(self, value: object) -> StatusCondition | None:
        if value is None:
            return None
        return self._parse_enum(value, StatusCondition, _STATUS_IDS, enum_name="StatusCondition")

    def _parse_log_type(self, value: object) -> LogType:
        return self._parse_enum(value, LogType, _LOG_TYPE_IDS, enum_name="LogType")

    def _parse_enum(
        self,
        value: object,
        enum_type: type[Enum],
        int_map: Mapping[int, Enum],
        *,
        enum_name: str,
    ):
        if isinstance(value, enum_type):
            return value
        if isinstance(value, int):
            if value in int_map:
                return int_map[value]
            raise InvalidObservationEnumError(f"Unknown {enum_name} integer value: {value}")
        if isinstance(value, str):
            candidate = value.strip().upper()
            if candidate in enum_type.__members__:
                return enum_type[candidate]
            raise InvalidObservationEnumError(f"Unknown {enum_name} string value: {value!r}")
        raise InvalidObservationEnumError(f"Unsupported {enum_name} value type: {type(value).__name__}")

    def _require_field(self, payload: Mapping[str, object], field_name: str, path: str) -> object:
        if field_name not in payload:
            raise MissingObservationFieldError(f"Missing required field {path}.{field_name}")
        return payload[field_name]

    def _require_mapping(self, value: object, *, path: str) -> Mapping[str, object]:
        if not isinstance(value, Mapping):
            raise CorruptedObservationError(f"{path} must be a mapping/object.")
        return value

    def _require_list(self, value: object, *, path: str) -> Sequence[object]:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            raise CorruptedObservationError(f"{path} must be a list/sequence.")
        return value

    def _require_int(self, payload: Mapping[str, object], field_name: str, path: str) -> int:
        value = self._require_field(payload, field_name, path)
        parsed = self._optional_int(value)
        if parsed is None:
            raise CorruptedObservationError(f"{path}.{field_name} must be an integer.")
        return parsed

    def _require_bool(self, payload: Mapping[str, object], field_name: str, path: str) -> bool:
        value = self._require_field(payload, field_name, path)
        parsed = self._optional_bool(value)
        if parsed is None:
            raise CorruptedObservationError(f"{path}.{field_name} must be a boolean.")
        return parsed

    def _optional_int(self, value: object) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().lstrip("-").isdigit():
            return int(value.strip())
        return None

    def _optional_bool(self, value: object) -> bool | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized == "true":
                return True
            if normalized == "false":
                return False
        return None

    def _optional_str(self, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return None

    def _remaining_fields(self, payload: Mapping[str, object], *, excluded: set[str]) -> Mapping[str, object]:
        return {key: value for key, value in payload.items() if key not in excluded}
