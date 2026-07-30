"""Unit tests for the card database."""

from __future__ import annotations

import csv
import sys
import unittest
import uuid
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from poketcg.cards import CardDatabase
from poketcg.cards.exceptions import CardDatabaseNotLoadedError, CardDataValidationError, MissingCardIdError
from poketcg.domain.enums import CardType, PokemonType, Stage


HEADER = (
    "Card ID",
    "Card Name",
    "Expansion",
    "Collection No.",
    "Stage (Pokémon)/Type (Energy and Trainer)",
    "Rule",
    "Category",
    "Previous stage",
    "HP",
    "Type",
    "Weakness",
    "Resistance (Type)",
    "Retreat",
    "Move Name",
    "Cost",
    "Damage",
    "Effect Explanation",
)


class CardDatabaseTestCase(unittest.TestCase):
    """Tests for loading, normalization, indexing, and validation."""

    def setUp(self) -> None:
        self.database = CardDatabase()

    def test_query_before_load_raises(self) -> None:
        with self.assertRaises(CardDatabaseNotLoadedError):
            self.database.count()

    def test_load_real_database(self) -> None:
        self.database.load()
        self.assertEqual(self.database.count(), 1267)
        self.assertTrue(self.database.exists(1))
        self.assertFalse(self.database.exists(99999))

    def test_get_returns_normalized_card(self) -> None:
        self.database.load()
        card = self.database.get(121)
        self.assertEqual(card.name, "Dragapult ex")
        self.assertEqual(card.card_type, CardType.POKEMON)
        self.assertEqual(card.stage, Stage.STAGE_2)
        self.assertEqual(card.pokemon_type, PokemonType.DRAGON)
        self.assertEqual(len(card.attacks), 2)
        self.assertEqual(len(card.abilities), 1)
        self.assertTrue(card.is_ex())
        self.assertTrue(card.is_tera())

    def test_zero_cost_attack_is_supported(self) -> None:
        self.database.load()
        card = self.database.get(183)
        self.assertEqual(card.name, "Smoochum")
        self.assertEqual(card.attacks[0].cost.total, 0)

    def test_exact_name_lookup_is_case_insensitive(self) -> None:
        self.database.load()
        cards = self.database.by_name("dragapult ex")
        self.assertGreaterEqual(len(cards), 1)
        self.assertEqual(cards[0].name, "Dragapult ex")

    def test_lookup_indexes(self) -> None:
        self.database.load()
        self.assertGreater(len(self.database.by_type(CardType.POKEMON)), 1000)
        self.assertGreater(len(self.database.by_stage(Stage.BASIC)), 500)
        self.assertGreater(len(self.database.by_pokemon_type(PokemonType.DRAGON)), 30)
        self.assertGreater(len(self.database.by_evolves_from("Frogadier")), 0)
        self.assertGreater(len(self.database.by_energy_type(PokemonType.RAINBOW)), 0)

    def test_search_helpers(self) -> None:
        self.database.load()
        self.assertTrue(any(card.name == "Dragapult ex" for card in self.database.find_prefix("Drag")))
        self.assertTrue(any("Ogerpon" in card.name for card in self.database.find_contains("oger")))
        self.assertTrue(any("Festival" in " ".join(ability.name for ability in card.abilities) or "Festival" in card.name for card in self.database.find_partial("festival")))
        self.assertTrue(any(card.name == "Teal Mask Ogerpon ex" for card in self.database.search("teal")))

    def test_random_returns_known_card(self) -> None:
        self.database.load()
        card = self.database.random()
        self.assertTrue(self.database.exists(card.card_id))

    def test_stats_are_available_after_load(self) -> None:
        self.database.load()
        self.assertEqual(self.database.stats.total_cards, 1267)
        self.assertEqual(self.database.stats.most_common_retreat_cost, 1)
        self.assertGreater(self.database.stats.average_hp or 0.0, 100.0)

    def test_missing_card_id_validation(self) -> None:
        rows = [
            self._build_row(card_id="", name="Broken Card"),
        ]
        with self.assertRaises(MissingCardIdError):
            self._load_from_rows(rows)

    def test_inconsistent_static_rows_raise(self) -> None:
        rows = [
            self._build_row(card_id="1", name="Card A", move_name="Attack 1", cost="{G}"),
            self._build_row(card_id="1", name="Card B", move_name="Attack 2", cost="{G}{G}"),
        ]
        with self.assertRaises(CardDataValidationError):
            self._load_from_rows(rows)

    def test_invalid_stage_raises(self) -> None:
        rows = [
            self._build_row(card_id="1", name="Broken Stage", stage_or_type="Legendary Pokemon"),
        ]
        with self.assertRaises(CardDataValidationError):
            self._load_from_rows(rows)

    def test_non_contiguous_card_ids_raise(self) -> None:
        rows = [
            self._build_row(card_id="1", name="Card One"),
            self._build_row(card_id="3", name="Card Three"),
        ]
        with self.assertRaises(MissingCardIdError):
            self._load_from_rows(rows)

    def _load_from_rows(self, rows: list[dict[str, str]]) -> CardDatabase:
        workspace_tmp = Path(__file__).resolve().parents[2] / "tests" / ".tmp"
        workspace_tmp.mkdir(parents=True, exist_ok=True)
        path = workspace_tmp / f"cards_{uuid.uuid4().hex}.csv"
        try:
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=HEADER)
                writer.writeheader()
                writer.writerows(rows)
            database = CardDatabase()
            database.load(path)
            return database
        finally:
            if path.exists():
                path.unlink()

    def _build_row(
        self,
        *,
        card_id: str,
        name: str,
        expansion: str = "TEST",
        collection_number: str = "1",
        stage_or_type: str = "Basic Pokémon",
        rule: str = "n/a",
        category: str = "n/a",
        previous_stage: str = "n/a",
        hp: str = "60",
        type_value: str = "{G}",
        weakness: str = "{R}",
        resistance: str = "n/a",
        retreat: str = "1",
        move_name: str = "n/a",
        cost: str = "n/a",
        damage: str = "n/a",
        effect_explanation: str = "n/a",
    ) -> dict[str, str]:
        return {
            "Card ID": card_id,
            "Card Name": name,
            "Expansion": expansion,
            "Collection No.": collection_number,
            "Stage (Pokémon)/Type (Energy and Trainer)": stage_or_type,
            "Rule": rule,
            "Category": category,
            "Previous stage": previous_stage,
            "HP": hp,
            "Type": type_value,
            "Weakness": weakness,
            "Resistance (Type)": resistance,
            "Retreat": retreat,
            "Move Name": move_name,
            "Cost": cost,
            "Damage": damage,
            "Effect Explanation": effect_explanation,
        }


if __name__ == "__main__":
    unittest.main()
