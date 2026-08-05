"""Tests for deck loading and legality validation."""

from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path
import uuid

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
TMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from poketcg.agent import BaselineAgentConfig, create_baseline_agent
from poketcg.cards import CardDatabase
from poketcg.deck import DeckLoader, DeckValidationError, DeckValidator
from poketcg.domain import Deck
from poketcg.debug.replay_logger import ReplayLoggerConfig


class DeckValidationTestCase(unittest.TestCase):
    """Verify deck legality checks and deck loading."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.card_database = CardDatabase()
        cls.card_database.load()
        cls.validator = DeckValidator(cls.card_database)

    def test_valid_baseline_deck_passes_validation(self) -> None:
        agent = create_baseline_agent(BaselineAgentConfig(replay=self._replay_config(enabled=False)))

        deck = agent.select_deck()
        result = self.validator.validate(deck)

        self.assertTrue(result.is_valid)
        self.assertEqual(result.issues, ())

    def test_invalid_size_raises(self) -> None:
        deck = Deck(card_ids=(1,) * 59, name="too_small")

        with self.assertRaisesRegex(DeckValidationError, "exactly 60"):
            self.validator.validate_or_raise(deck)

    def test_duplicate_copy_limit_raises(self) -> None:
        deck = Deck(card_ids=(1077,) * 5 + (3,) * 55, name="too_many_items")

        with self.assertRaisesRegex(DeckValidationError, "maximum copy limit"):
            self.validator.validate_or_raise(deck)

    def test_ace_spec_limit_raises(self) -> None:
        deck = Deck(card_ids=(1080,) * 2 + (3,) * 58, name="too_many_ace_spec")

        with self.assertRaisesRegex(DeckValidationError, "ACE SPEC card"):
            self.validator.validate_or_raise(deck)

    def test_duplicate_validation_reports_card_details(self) -> None:
        deck = Deck(card_ids=(1077,) * 5 + (3,) * 55, name="too_many_items")

        result = self.validator.validate(deck)
        issue = next(issue for issue in result.issues if issue.card_id == 1077)

        self.assertEqual(issue.card_name, "Roto-Stick")
        self.assertEqual(issue.copies_found, 5)
        self.assertEqual(issue.maximum_allowed, 4)

    def test_loader_loads_and_validates_a_deck_file(self) -> None:
        agent = create_baseline_agent(BaselineAgentConfig(replay=self._replay_config(enabled=False)))
        deck = list(agent.select_deck().card_ids)

        temp_dir = self._make_temp_dir()
        try:
            path = temp_dir / "deck.csv"
            path.write_text("\n".join(str(card_id) for card_id in deck) + "\n", encoding="utf-8")

            loader = DeckLoader(self.card_database)
            loaded = loader.load(path)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        self.assertEqual(loaded.card_ids, tuple(deck))

    def test_loader_rejects_illegal_deck(self) -> None:
        temp_dir = self._make_temp_dir()
        try:
            path = temp_dir / "deck.csv"
            path.write_text("\n".join([str(1080), str(1080)] + ["3"] * 58) + "\n", encoding="utf-8")

            loader = DeckLoader(self.card_database)
            with self.assertRaisesRegex(DeckValidationError, "ACE SPEC card"):
                loader.load(path)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _replay_config(self, *, enabled: bool = True):
        return ReplayLoggerConfig(
            enabled=enabled,
            output_directory=Path("outputs/replays"),
            markdown=True,
            json=True,
            maximum_saved_games=10,
        )

    def _make_temp_dir(self) -> Path:
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        path = TMP_ROOT / f"deck_{uuid.uuid4().hex}"
        path.mkdir(parents=True, exist_ok=True)
        return path


if __name__ == "__main__":
    unittest.main()
