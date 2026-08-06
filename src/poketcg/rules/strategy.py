"""Shared factual helpers for rule-library heuristics."""

from __future__ import annotations

import re

from poketcg.actions import AttackAction, AttachEnergyAction, EvolutionAction, PlayCardAction, RetreatAction
from poketcg.cards.models import CardData
from poketcg.domain import Card, Pokemon

_POSITIVE_SUPPORTER_KEYWORDS = (
    "draw",
    "search",
    "shuffle",
    "discard your hand",
    "put",  # broad but useful for tutor/search supporters
)


def attack_damage_value(action: AttackAction) -> int | None:
    """Return the numeric damage value for an attack action, if available."""

    if action.attack is not None and action.attack.damage_value is not None:
        return action.attack.damage_value
    if action.damage is None:
        return None
    match = re.search(r"-?\d+", action.damage.replace(",", ""))
    if match is None:
        return None
    try:
        return int(match.group(0))
    except ValueError:
        return None


def attack_energy_cost(action: AttackAction) -> int:
    """Return the printed energy-symbol count for an attack action."""

    if action.attack is not None:
        return len(action.attack.cost.symbols)
    return len(action.energy_cost)


def attack_overkill(action: AttackAction, opponent_hp: int) -> int | None:
    """Return excess damage over the opponent's remaining HP."""

    damage = attack_damage_value(action)
    if damage is None:
        return None
    return damage - opponent_hp


def attack_is_lethal(action: AttackAction, opponent_hp: int) -> bool:
    """Return whether an attack knocks out the active opponent Pokémon."""

    damage = attack_damage_value(action)
    return damage is not None and damage >= opponent_hp


def attack_priority_score(action: AttackAction, opponent_hp: int) -> tuple[int, int, int, int]:
    """Return a comparable score for attack-based rules.

    Higher is better.
    """

    damage = attack_damage_value(action) or 0
    lethal = 1 if damage >= opponent_hp and damage > 0 else 0
    overkill = max(damage - opponent_hp, 0) if damage > 0 else 0
    return lethal, damage, -overkill, -attack_energy_cost(action)


def pokemon_attack_potential(pokemon: Pokemon | None) -> int:
    """Return the highest printed attack damage for a Pokémon."""

    if pokemon is None:
        return 0
    damage_values = [attack.damage_value for attack in pokemon.card.metadata.attacks if attack.damage_value is not None]
    return max(damage_values, default=0)


def pokemon_attack_cost_floor(pokemon: Pokemon | None) -> int | None:
    """Return the lowest printed energy cost among a Pokémon's attacks."""

    if pokemon is None or not pokemon.card.metadata.attacks:
        return None
    return min(len(attack.cost.symbols) for attack in pokemon.card.metadata.attacks)


def pokemon_attack_gap(pokemon: Pokemon | None) -> int | None:
    """Return how many more energy cards the Pokémon needs to reach its cheapest attack."""

    if pokemon is None:
        return None
    floor = pokemon_attack_cost_floor(pokemon)
    if floor is None:
        return None
    current_energy = max(len(pokemon.attached_energy_cards), len(pokemon.attached_energy_types))
    return max(floor - current_energy, 0)


def pokemon_board_value(pokemon: Pokemon | None) -> tuple[int, int, int]:
    """Return a rough board-value tuple for choosing between Pokémon."""

    if pokemon is None:
        return (0, 0, 0)
    return (
        pokemon.current_hp,
        pokemon_attack_potential(pokemon),
        max(len(pokemon.attached_energy_cards), len(pokemon.attached_energy_types)),
    )


def card_attack_potential(card: Card | CardData | None) -> int:
    """Return the highest printed attack damage for a card or card metadata."""

    if card is None:
        return 0
    metadata = card.metadata if isinstance(card, Card) else card
    damage_values = [attack.damage_value for attack in metadata.attacks if attack.damage_value is not None]
    return max(damage_values, default=0)


def evolution_board_value(target: Pokemon | None, evolution_card: Card | CardData | None) -> tuple[int, int, int]:
    """Return a comparable value for deciding whether evolution is worthwhile."""

    if target is None or evolution_card is None:
        return (0, 0, 0)
    metadata = evolution_card.metadata if isinstance(evolution_card, Card) else evolution_card
    evolved_hp = metadata.hp or target.max_hp
    hp_gain = max(evolved_hp - target.max_hp, 0)
    attack_gain = max(card_attack_potential(metadata) - pokemon_attack_potential(target), 0)
    current_energy = max(len(target.attached_energy_cards), len(target.attached_energy_types))
    return (hp_gain, attack_gain, current_energy)


def supporter_is_beneficial(card: Card) -> bool:
    """Return whether a supporter looks like a draw/search/tutor supporter."""

    metadata = card.metadata
    haystacks = " ".join(
        part
        for part in (
            metadata.name,
            metadata.effect_text or "",
            metadata.rule or "",
            metadata.category or "",
        )
    ).casefold()
    return any(keyword in haystacks for keyword in _POSITIVE_SUPPORTER_KEYWORDS)


def supporter_score(card: Card) -> tuple[int, int]:
    """Return a comparable score for Supporter selection."""

    metadata = card.metadata
    haystack = " ".join(
        part
        for part in (
            metadata.name,
            metadata.effect_text or "",
            metadata.rule or "",
            metadata.category or "",
        )
    ).casefold()
    score = sum(1 for keyword in _POSITIVE_SUPPORTER_KEYWORDS if keyword in haystack)
    return score, len(haystack)
