"""Normalization helpers for card metadata."""

from __future__ import annotations

import re
from typing import Final

from poketcg.domain.enums import CardType, PokemonType, Stage

from .exceptions import CardDataValidationError
from .models import EnergyCost


_TYPE_TOKEN_MAP: Final[dict[str, PokemonType]] = {
    "{C}": PokemonType.COLORLESS,
    "{G}": PokemonType.GRASS,
    "{R}": PokemonType.FIRE,
    "{W}": PokemonType.WATER,
    "{L}": PokemonType.LIGHTNING,
    "{P}": PokemonType.PSYCHIC,
    "{F}": PokemonType.FIGHTING,
    "{D}": PokemonType.DARKNESS,
    "{M}": PokemonType.METAL,
    "竜": PokemonType.DRAGON,
    "{A}": PokemonType.RAINBOW,
    "{Team Rocket}": PokemonType.TEAM_ROCKET,
    "●": PokemonType.COLORLESS,
}

_TOKEN_PATTERN: Final[re.Pattern[str]] = re.compile(r"\{[^}]+\}|竜|●")

_STAGE_MAP: Final[dict[str, Stage | None]] = {
    "Basic Pokemon": Stage.BASIC,
    "Stage 1 Pokemon": Stage.STAGE_1,
    "Stage 2 Pokemon": Stage.STAGE_2,
    "Basic Energy": None,
    "Special Energy": None,
    "Item": None,
    "Supporter": None,
    "Pokemon Tool": None,
    "Stadium": None,
}

_CARD_TYPE_MAP: Final[dict[str, CardType]] = {
    "Basic Pokemon": CardType.POKEMON,
    "Stage 1 Pokemon": CardType.POKEMON,
    "Stage 2 Pokemon": CardType.POKEMON,
    "Item": CardType.ITEM,
    "Supporter": CardType.SUPPORTER,
    "Pokemon Tool": CardType.TOOL,
    "Stadium": CardType.STADIUM,
    "Special Energy": CardType.SPECIAL_ENERGY,
    "Basic Energy": CardType.BASIC_ENERGY,
}


def normalize_unicode_text(value: str) -> str:
    """Normalize known source-specific unicode variants to stable ASCII tokens."""

    return (
        value.replace("Pokémon", "Pokemon")
        .replace("’", "'")
        .replace("\uff08", "(")
        .replace("\uff09", ")")
    )


def clean_optional_text(value: str) -> str | None:
    """Convert blank or n/a-like strings to None."""

    stripped = normalize_unicode_text(value).strip()
    if not stripped or stripped.lower() == "n/a":
        return None
    return stripped


def parse_card_type(raw_stage_or_type: str) -> CardType:
    """Parse card type from the stage/type column."""

    normalized = normalize_unicode_text(raw_stage_or_type)
    try:
        return _CARD_TYPE_MAP[normalized]
    except KeyError as exc:
        raise CardDataValidationError(f"Invalid stage/type value: {raw_stage_or_type!r}") from exc


def parse_stage(raw_stage_or_type: str) -> Stage | None:
    """Parse Pokemon stage from the stage/type column."""

    normalized = normalize_unicode_text(raw_stage_or_type)
    if normalized not in _STAGE_MAP:
        raise CardDataValidationError(f"Invalid stage/type value: {raw_stage_or_type!r}")
    return _STAGE_MAP[normalized]


def parse_int_field(value: str, *, field_name: str) -> int | None:
    """Parse a possibly optional integer field."""

    cleaned = clean_optional_text(value)
    if cleaned is None:
        return None
    if not cleaned.isdigit():
        raise CardDataValidationError(f"Invalid integer value for {field_name}: {value!r}")
    return int(cleaned)


def parse_damage_value(value: str) -> int | None:
    """Extract a numeric damage prefix when available."""

    cleaned = clean_optional_text(value)
    if cleaned is None:
        return None
    digits = []
    for character in cleaned:
        if character.isdigit():
            digits.append(character)
        else:
            break
    if not digits:
        return None
    return int("".join(digits))


def parse_energy_tokens(raw: str) -> tuple[PokemonType, ...]:
    """Parse one or more energy symbols from a raw token string."""

    cleaned = clean_optional_text(raw)
    if cleaned is None:
        return ()

    tokens = _TOKEN_PATTERN.findall(cleaned)
    if not tokens:
        raise CardDataValidationError(f"Invalid energy token string: {raw!r}")

    parsed: list[PokemonType] = []
    for token in tokens:
        try:
            parsed.append(_TYPE_TOKEN_MAP[token])
        except KeyError as exc:
            raise CardDataValidationError(f"Unknown energy token {token!r} in {raw!r}") from exc
    return tuple(parsed)


def parse_energy_cost(raw: str) -> EnergyCost | None:
    """Parse an attack-cost field."""

    cleaned = clean_optional_text(raw)
    if cleaned is None:
        return None
    if cleaned.casefold() == "no cost":
        return EnergyCost(raw=cleaned, symbols=())
    return EnergyCost(raw=cleaned, symbols=parse_energy_tokens(cleaned))


def parse_primary_pokemon_type(raw: str) -> PokemonType | None:
    """Parse a primary Pokemon type when the raw value represents exactly one type."""

    symbols = parse_energy_tokens(raw)
    if len(symbols) != 1:
        return None
    return symbols[0]


def normalize_name_key(value: str) -> str:
    """Normalize a name-like string for case-insensitive indexing."""

    normalized = normalize_unicode_text(value)
    return " ".join(normalized.casefold().split())


def tokenize_search_text(value: str) -> tuple[str, ...]:
    """Split a search string into lowercase alphanumeric tokens."""

    normalized = normalize_name_key(value)
    tokens = re.findall(r"[a-z0-9']+", normalized)
    return tuple(token for token in tokens if token)
