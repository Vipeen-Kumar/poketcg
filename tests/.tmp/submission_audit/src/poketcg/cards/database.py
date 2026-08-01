"""Normalized read-optimized card database."""

from __future__ import annotations

import random as random_module
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from poketcg.config import get_default_config
from poketcg.domain.enums import CardType, PokemonType, Stage

from .exceptions import (
    CardDataValidationError,
    CardDatabaseNotLoadedError,
    CorruptedCardRowError,
    MissingCardIdError,
    UnknownCardLookupError,
)
from .interfaces import BaseCardCatalog, BaseCardDataCache, BaseCardDataSource
from .models import (
    AbilityData,
    AttackData,
    CardData,
    EvolutionData,
    ResistanceData,
    RetreatCost,
    WeaknessData,
)
from .normalization import (
    clean_optional_text,
    normalize_name_key,
    normalize_unicode_text,
    parse_card_type,
    parse_damage_value,
    parse_energy_cost,
    parse_energy_tokens,
    parse_int_field,
    parse_primary_pokemon_type,
    parse_stage,
    tokenize_search_text,
)
from .sources import CsvCardDataSource
from .statistics import CardDatabaseStats, build_card_database_stats


class CardDatabase(BaseCardCatalog):
    """Load-once, read-optimized static card metadata database."""

    def __init__(
        self,
        source: BaseCardDataSource | None = None,
        *,
        cache: BaseCardDataCache | None = None,
    ) -> None:
        config = get_default_config()
        self._source = source or CsvCardDataSource(config.paths.english_card_csv)
        self._cache = cache
        self._loaded = False
        self._cards: tuple[CardData, ...] = ()
        self._cards_by_id: dict[int, CardData] = {}
        self._cards_by_name: dict[str, tuple[CardData, ...]] = {}
        self._cards_by_type: dict[CardType, tuple[CardData, ...]] = {}
        self._cards_by_stage: dict[Stage, tuple[CardData, ...]] = {}
        self._cards_by_pokemon_type: dict[PokemonType, tuple[CardData, ...]] = {}
        self._cards_by_evolves_from: dict[str, tuple[CardData, ...]] = {}
        self._cards_by_energy_type: dict[PokemonType, tuple[CardData, ...]] = {}
        self._prefix_index: dict[str, tuple[int, ...]] = {}
        self._contains_index: dict[str, tuple[int, ...]] = {}
        self._keyword_index: dict[str, tuple[int, ...]] = {}
        self._stats: CardDatabaseStats | None = None

    def load(self, path: Path | None = None) -> None:
        """Load and normalize card data from the configured source."""

        if path is not None:
            self._source = CsvCardDataSource(path)

        rows = self._source.load_rows()
        cards = self._build_cards(rows)
        self._cards = tuple(sorted(cards.values(), key=lambda card: card.card_id))
        self._cards_by_id = dict(cards)
        self._build_indexes(self._cards)
        self._stats = build_card_database_stats(self._cards)
        self._loaded = True

    def get(self, card_id: int) -> CardData:
        """Return a card by id."""

        self._ensure_loaded()
        try:
            return self._cards_by_id[card_id]
        except KeyError as exc:
            raise UnknownCardLookupError(f"Unknown card id: {card_id}") from exc

    def exists(self, card_id: int) -> bool:
        """Return whether a card id is present."""

        self._ensure_loaded()
        return card_id in self._cards_by_id

    def by_name(self, name: str) -> tuple[CardData, ...]:
        """Return cards with an exact case-insensitive name match."""

        self._ensure_loaded()
        return self._cards_by_name.get(normalize_name_key(name), ())

    def find_exact(self, name: str) -> tuple[CardData, ...]:
        """Alias for exact name lookup."""

        return self.by_name(name)

    def by_type(self, card_type: CardType) -> tuple[CardData, ...]:
        """Return cards by card type."""

        self._ensure_loaded()
        return self._cards_by_type.get(card_type, ())

    def by_stage(self, stage: Stage) -> tuple[CardData, ...]:
        """Return cards by Pokemon stage."""

        self._ensure_loaded()
        return self._cards_by_stage.get(stage, ())

    def by_pokemon_type(self, pokemon_type: PokemonType) -> tuple[CardData, ...]:
        """Return cards by Pokemon type."""

        self._ensure_loaded()
        return self._cards_by_pokemon_type.get(pokemon_type, ())

    def by_energy_type(self, pokemon_type: PokemonType) -> tuple[CardData, ...]:
        """Return cards indexed by energy type symbols."""

        self._ensure_loaded()
        return self._cards_by_energy_type.get(pokemon_type, ())

    def by_evolves_from(self, name: str) -> tuple[CardData, ...]:
        """Return cards that evolve from the given base name."""

        self._ensure_loaded()
        return self._cards_by_evolves_from.get(normalize_name_key(name), ())

    def find_prefix(self, prefix: str) -> tuple[CardData, ...]:
        """Return cards whose names start with the given prefix."""

        self._ensure_loaded()
        card_ids = self._prefix_index.get(normalize_name_key(prefix), ())
        return self._resolve_card_ids(card_ids)

    def find_contains(self, text: str) -> tuple[CardData, ...]:
        """Return cards whose names contain the given case-insensitive substring."""

        self._ensure_loaded()
        card_ids = self._contains_index.get(normalize_name_key(text), ())
        return self._resolve_card_ids(card_ids)

    def find_partial(self, text: str) -> tuple[CardData, ...]:
        """Return cards matching the text by name contains or keyword token."""

        self._ensure_loaded()
        normalized = normalize_name_key(text)
        contains_ids = set(self._contains_index.get(normalized, ()))
        keyword_ids = set()
        for token in tokenize_search_text(text):
            keyword_ids.update(self._keyword_index.get(token, ()))
        return self._resolve_card_ids(sorted(contains_ids | keyword_ids))

    def search(self, keyword: str) -> tuple[CardData, ...]:
        """Search cards using exact, prefix, contains, and token indexes."""

        self._ensure_loaded()
        normalized = normalize_name_key(keyword)
        card_ids = set()
        card_ids.update(card.card_id for card in self.by_name(keyword))
        card_ids.update(self._prefix_index.get(normalized, ()))
        card_ids.update(self._contains_index.get(normalized, ()))
        for token in tokenize_search_text(keyword):
            card_ids.update(self._keyword_index.get(token, ()))
        return self._resolve_card_ids(sorted(card_ids))

    def all_cards(self) -> tuple[CardData, ...]:
        """Return all normalized cards."""

        self._ensure_loaded()
        return self._cards

    def count(self) -> int:
        """Return the number of unique cards."""

        self._ensure_loaded()
        return len(self._cards)

    def random(self, rng: random_module.Random | None = None) -> CardData:
        """Return a random card."""

        self._ensure_loaded()
        chooser = rng or random_module
        return chooser.choice(self._cards)

    @property
    def stats(self) -> CardDatabaseStats:
        """Return computed card-database statistics."""

        self._ensure_loaded()
        if self._stats is None:
            raise CardDatabaseNotLoadedError("Card database statistics are unavailable before loading.")
        return self._stats

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            raise CardDatabaseNotLoadedError("CardDatabase.load() must be called before querying card metadata.")

    def _resolve_card_ids(self, card_ids: Iterable[int]) -> tuple[CardData, ...]:
        ordered = sorted(set(card_ids))
        return tuple(self._cards_by_id[card_id] for card_id in ordered)

    def _build_cards(self, rows: Sequence[Mapping[str, str]]) -> dict[int, CardData]:
        if not rows:
            raise CardDataValidationError("Card data source returned no rows.")

        grouped: dict[int, list[Mapping[str, str]]] = defaultdict(list)
        seen_ids: set[int] = set()
        for index, row in enumerate(rows, start=1):
            card_id_raw = row.get("Card ID", "").strip()
            if not card_id_raw:
                raise MissingCardIdError(f"Missing card id in row {index}.")
            if not card_id_raw.isdigit():
                raise MissingCardIdError(f"Invalid card id {card_id_raw!r} in row {index}.")
            grouped[int(card_id_raw)].append(row)
            seen_ids.add(int(card_id_raw))

        card_ids = sorted(seen_ids)
        if card_ids != list(range(card_ids[0], card_ids[-1] + 1)):
            raise MissingCardIdError("Card ids must form a contiguous range in EN_Card_Data.csv.")

        cards: dict[int, CardData] = {}
        for card_id, group in grouped.items():
            cards[card_id] = self._build_card(card_id=card_id, rows=group)
        return cards

    def _build_card(self, *, card_id: int, rows: Sequence[Mapping[str, str]]) -> CardData:
        base_row = rows[0]
        stage_field = "Stage (Pok\u00e9mon)/Type (Energy and Trainer)"
        static_columns = (
            "Card Name",
            "Expansion",
            "Collection No.",
            stage_field,
            "Rule",
            "Category",
            "Previous stage",
            "HP",
            "Type",
            "Weakness",
            "Resistance (Type)",
            "Retreat",
        )

        for column in static_columns:
            values = {row[column] for row in rows}
            if len(values) != 1:
                raise CorruptedCardRowError(
                    f"Card ID {card_id} has inconsistent static field {column!r}: {sorted(values)!r}"
                )

        name = clean_optional_text(base_row["Card Name"])
        if name is None:
            raise CorruptedCardRowError(f"Card ID {card_id} has an empty name.")

        raw_stage_or_type = normalize_unicode_text(base_row[stage_field])
        raw_type = normalize_unicode_text(base_row["Type"])
        card_type = parse_card_type(raw_stage_or_type)
        stage = parse_stage(raw_stage_or_type)
        hp = parse_int_field(base_row["HP"], field_name="HP")
        retreat_value = parse_int_field(base_row["Retreat"], field_name="Retreat")
        weakness = self._build_weakness(base_row["Weakness"])
        resistance = self._build_resistance(base_row["Resistance (Type)"])
        energy_types = parse_energy_tokens(raw_type) if clean_optional_text(raw_type) is not None else ()
        pokemon_type = None
        if card_type in {CardType.POKEMON, CardType.BASIC_ENERGY}:
            pokemon_type = parse_primary_pokemon_type(raw_type)

        attacks: list[AttackData] = []
        abilities: list[AbilityData] = []
        effect_text = None

        for row in rows:
            move_name = clean_optional_text(row["Move Name"])
            move_cost = parse_energy_cost(row["Cost"])
            move_damage = clean_optional_text(row["Damage"])
            move_effect = clean_optional_text(row["Effect Explanation"])

            if move_name is None:
                if effect_text is None:
                    effect_text = move_effect
                continue

            if card_type is CardType.POKEMON and move_cost is None:
                abilities.append(self._build_ability(move_name, move_effect))
                continue

            if move_cost is None:
                if effect_text is None:
                    effect_text = move_effect
                continue

            attacks.append(
                AttackData(
                    name=move_name,
                    text=move_effect,
                    cost=move_cost,
                    damage=move_damage,
                    damage_value=parse_damage_value(row["Damage"]),
                )
            )

        return CardData(
            card_id=card_id,
            name=name,
            expansion=clean_optional_text(base_row["Expansion"]),
            collection_number=normalize_unicode_text(base_row["Collection No."]).strip(),
            card_type=card_type,
            stage=stage,
            pokemon_type=pokemon_type,
            energy_types=energy_types,
            rule=clean_optional_text(base_row["Rule"]),
            category=clean_optional_text(base_row["Category"]),
            hp=hp,
            weakness=weakness,
            resistance=resistance,
            retreat_cost=RetreatCost(retreat_value) if retreat_value is not None else None,
            evolution=EvolutionData(evolves_from=clean_optional_text(base_row["Previous stage"])),
            attacks=tuple(attacks),
            abilities=tuple(abilities),
            effect_text=effect_text,
            raw_stage_or_type=raw_stage_or_type,
            raw_type=raw_type,
        )

    def _build_weakness(self, raw_value: str) -> WeaknessData | None:
        cleaned = clean_optional_text(raw_value)
        if cleaned is None:
            return None
        symbols = parse_energy_tokens(cleaned)
        if len(symbols) != 1:
            raise CardDataValidationError(f"Weakness must contain exactly one type: {raw_value!r}")
        return WeaknessData(symbols[0])

    def _build_resistance(self, raw_value: str) -> ResistanceData | None:
        cleaned = clean_optional_text(raw_value)
        if cleaned is None:
            return None
        symbols = parse_energy_tokens(cleaned)
        if len(symbols) != 1:
            raise CardDataValidationError(f"Resistance must contain exactly one type: {raw_value!r}")
        return ResistanceData(symbols[0])

    def _build_ability(self, move_name: str, effect_text: str | None) -> AbilityData:
        normalized_name = normalize_unicode_text(move_name)
        if normalized_name.startswith("[Ability] "):
            return AbilityData(name=normalized_name.removeprefix("[Ability] ").strip(), text=effect_text, kind="ability")
        if normalized_name == "[Tera]":
            return AbilityData(name="Tera", text=effect_text, kind="tera")
        return AbilityData(name=normalized_name, text=effect_text, kind="text")

    def _build_indexes(self, cards: Sequence[CardData]) -> None:
        by_name: dict[str, list[CardData]] = defaultdict(list)
        by_type: dict[CardType, list[CardData]] = defaultdict(list)
        by_stage: dict[Stage, list[CardData]] = defaultdict(list)
        by_pokemon_type: dict[PokemonType, list[CardData]] = defaultdict(list)
        by_evolves_from: dict[str, list[CardData]] = defaultdict(list)
        by_energy_type: dict[PokemonType, list[CardData]] = defaultdict(list)
        prefix_index: dict[str, set[int]] = defaultdict(set)
        contains_index: dict[str, set[int]] = defaultdict(set)
        keyword_index: dict[str, set[int]] = defaultdict(set)

        for card in cards:
            name_key = normalize_name_key(card.name)
            by_name[name_key].append(card)
            by_type[card.card_type].append(card)
            if card.stage is not None:
                by_stage[card.stage].append(card)
            if card.pokemon_type is not None:
                by_pokemon_type[card.pokemon_type].append(card)
            if card.evolution.evolves_from is not None:
                by_evolves_from[normalize_name_key(card.evolution.evolves_from)].append(card)
            for energy_type in card.energy_types:
                by_energy_type[energy_type].append(card)

            for end in range(1, len(name_key) + 1):
                prefix_index[name_key[:end]].add(card.card_id)

            for start in range(len(name_key)):
                for end in range(start + 1, len(name_key) + 1):
                    substring = name_key[start:end]
                    if substring.strip():
                        contains_index[substring].add(card.card_id)

            keyword_fields = [card.name]
            if card.expansion is not None:
                keyword_fields.append(card.expansion)
            if card.category is not None:
                keyword_fields.append(card.category)
            if card.rule is not None:
                keyword_fields.append(card.rule)
            if card.evolution.evolves_from is not None:
                keyword_fields.append(card.evolution.evolves_from)
            if card.effect_text is not None:
                keyword_fields.append(card.effect_text)
            keyword_fields.extend(attack.name for attack in card.attacks)
            keyword_fields.extend(attack.text for attack in card.attacks if attack.text is not None)
            keyword_fields.extend(ability.name for ability in card.abilities)
            keyword_fields.extend(ability.text for ability in card.abilities if ability.text is not None)

            for field in keyword_fields:
                for token in tokenize_search_text(field):
                    keyword_index[token].add(card.card_id)

        self._cards_by_name = {key: tuple(value) for key, value in by_name.items()}
        self._cards_by_type = {key: tuple(value) for key, value in by_type.items()}
        self._cards_by_stage = {key: tuple(value) for key, value in by_stage.items()}
        self._cards_by_pokemon_type = {key: tuple(value) for key, value in by_pokemon_type.items()}
        self._cards_by_evolves_from = {key: tuple(value) for key, value in by_evolves_from.items()}
        self._cards_by_energy_type = {key: tuple(value) for key, value in by_energy_type.items()}
        self._prefix_index = {key: tuple(sorted(value)) for key, value in prefix_index.items()}
        self._contains_index = {key: tuple(sorted(value)) for key, value in contains_index.items()}
        self._keyword_index = {key: tuple(sorted(value)) for key, value in keyword_index.items()}
