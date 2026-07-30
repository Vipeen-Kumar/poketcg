"""Statistics helpers for the card database."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from poketcg.domain.enums import CardType, PokemonType, Stage

from .models import CardData


@dataclass(slots=True, frozen=True)
class CardDatabaseStats:
    """Aggregate statistics for a loaded card database."""

    total_cards: int
    pokemon_count: int
    trainer_count: int
    energy_count: int
    stage_distribution: dict[str, int]
    pokemon_type_distribution: dict[str, int]
    most_common_retreat_cost: int | None
    average_hp: float | None
    evolution_count: int
    basic_count: int
    stage1_count: int
    stage2_count: int
    missing_expansion_count: int
    missing_hp_count: int
    missing_weakness_count: int
    missing_resistance_count: int
    missing_retreat_count: int
    unknown_type_count: int


def build_card_database_stats(cards: tuple[CardData, ...]) -> CardDatabaseStats:
    """Build aggregate statistics from normalized card metadata."""

    total_cards = len(cards)
    pokemon_cards = [card for card in cards if card.card_type is CardType.POKEMON]
    trainer_cards = [card for card in cards if card.is_trainer()]
    energy_cards = [card for card in cards if card.is_energy()]

    stage_counter: Counter[str] = Counter()
    type_counter: Counter[str] = Counter()
    retreat_counter: Counter[int] = Counter()
    hp_values: list[int] = []
    evolution_count = 0
    missing_expansion_count = 0
    missing_hp_count = 0
    missing_weakness_count = 0
    missing_resistance_count = 0
    missing_retreat_count = 0
    unknown_type_count = 0

    for card in cards:
        if card.stage is Stage.BASIC:
            stage_counter["basic"] += 1
        elif card.stage is Stage.STAGE_1:
            stage_counter["stage1"] += 1
        elif card.stage is Stage.STAGE_2:
            stage_counter["stage2"] += 1
        else:
            stage_counter["non_pokemon_or_other"] += 1

        if card.pokemon_type is not None:
            type_counter[card.pokemon_type.name.lower()] += 1
        if card.expansion is None:
            missing_expansion_count += 1
        if card.hp is None:
            missing_hp_count += 1
        else:
            hp_values.append(card.hp)
        if card.weakness is None:
            missing_weakness_count += 1
        if card.resistance is None:
            missing_resistance_count += 1
        if card.retreat_cost is None:
            missing_retreat_count += 1
        else:
            retreat_counter[card.retreat_cost.colorless] += 1
        if card.evolution.evolves_from is not None:
            evolution_count += 1
        if card.pokemon_type is None and card.card_type is CardType.POKEMON:
            unknown_type_count += 1

    average_hp = None
    if hp_values:
        average_hp = sum(hp_values) / len(hp_values)

    most_common_retreat_cost = None
    if retreat_counter:
        most_common_retreat_cost = retreat_counter.most_common(1)[0][0]

    return CardDatabaseStats(
        total_cards=total_cards,
        pokemon_count=len(pokemon_cards),
        trainer_count=len(trainer_cards),
        energy_count=len(energy_cards),
        stage_distribution=dict(stage_counter),
        pokemon_type_distribution=dict(type_counter),
        most_common_retreat_cost=most_common_retreat_cost,
        average_hp=average_hp,
        evolution_count=evolution_count,
        basic_count=stage_counter.get("basic", 0),
        stage1_count=stage_counter.get("stage1", 0),
        stage2_count=stage_counter.get("stage2", 0),
        missing_expansion_count=missing_expansion_count,
        missing_hp_count=missing_hp_count,
        missing_weakness_count=missing_weakness_count,
        missing_resistance_count=missing_resistance_count,
        missing_retreat_count=missing_retreat_count,
        unknown_type_count=unknown_type_count,
    )
