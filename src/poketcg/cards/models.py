"""Static card metadata models."""

from __future__ import annotations

from dataclasses import dataclass

from poketcg.domain.enums import CardType, PokemonType, Stage


@dataclass(slots=True, frozen=True)
class EnergyCost:
    """Typed representation of a cost or provided energy string."""

    raw: str
    symbols: tuple[PokemonType, ...]

    @property
    def total(self) -> int:
        """Return the total number of energy symbols."""

        return len(self.symbols)


@dataclass(slots=True, frozen=True)
class WeaknessData:
    """Weakness metadata."""

    pokemon_type: PokemonType


@dataclass(slots=True, frozen=True)
class ResistanceData:
    """Resistance metadata."""

    pokemon_type: PokemonType


@dataclass(slots=True, frozen=True)
class RetreatCost:
    """Retreat-cost metadata."""

    colorless: int


@dataclass(slots=True, frozen=True)
class EvolutionData:
    """Evolution-chain metadata."""

    evolves_from: str | None = None


@dataclass(slots=True, frozen=True)
class AttackData:
    """Attack metadata extracted from the source CSV."""

    name: str
    text: str | None
    cost: EnergyCost
    damage: str | None = None
    damage_value: int | None = None


@dataclass(slots=True, frozen=True)
class AbilityData:
    """Ability-like or passive text entry metadata."""

    name: str
    text: str | None
    kind: str


@dataclass(slots=True, frozen=True)
class CardData:
    """Normalized static card metadata."""

    card_id: int
    name: str
    expansion: str | None
    collection_number: str
    card_type: CardType
    stage: Stage | None
    pokemon_type: PokemonType | None
    energy_types: tuple[PokemonType, ...]
    rule: str | None
    category: str | None
    hp: int | None
    weakness: WeaknessData | None
    resistance: ResistanceData | None
    retreat_cost: RetreatCost | None
    evolution: EvolutionData
    attacks: tuple[AttackData, ...]
    abilities: tuple[AbilityData, ...]
    effect_text: str | None
    raw_stage_or_type: str
    raw_type: str

    def is_basic(self) -> bool:
        return self.stage is Stage.BASIC

    def is_stage1(self) -> bool:
        return self.stage is Stage.STAGE_1

    def is_stage2(self) -> bool:
        return self.stage is Stage.STAGE_2

    def is_ex(self) -> bool:
        return self.rule == "Pokemon ex" or self.rule == "Mega Pokemon ex" or self.name.endswith(" ex")

    def is_mega_ex(self) -> bool:
        return self.rule == "Mega Pokemon ex"

    def is_tera(self) -> bool:
        if self.category is not None and self.category.startswith("Tera"):
            return True
        return any(ability.kind == "tera" for ability in self.abilities)

    def is_energy(self) -> bool:
        return self.card_type in {CardType.BASIC_ENERGY, CardType.SPECIAL_ENERGY}

    def is_trainer(self) -> bool:
        return self.card_type in {CardType.ITEM, CardType.TOOL, CardType.SUPPORTER, CardType.STADIUM}

    def is_supporter(self) -> bool:
        return self.card_type is CardType.SUPPORTER

    def is_item(self) -> bool:
        return self.card_type is CardType.ITEM

    def is_stadium(self) -> bool:
        return self.card_type is CardType.STADIUM

    def is_tool(self) -> bool:
        return self.card_type is CardType.TOOL

    def is_pokemon(self) -> bool:
        return self.card_type is CardType.POKEMON

    def is_ace_spec(self) -> bool:
        return self.rule == "ACE SPEC" or self.category == "ACE SPEC"
