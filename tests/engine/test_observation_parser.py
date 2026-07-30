"""Unit tests for the observation parser."""

from __future__ import annotations

import unittest

from poketcg.cards import CardDatabase
from poketcg.domain import GamePhase, OptionType, PlayerSide, PokemonType, SelectContext, SelectType, StatusCondition, Zone
from poketcg.engine import (
    CorruptedObservationError,
    InvalidObservationEnumError,
    MissingObservationCardError,
    MissingObservationFieldError,
    ObservationParser,
)


class ObservationParserTestCase(unittest.TestCase):
    """Tests for raw observation parsing."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.card_database = CardDatabase()
        cls.card_database.load()

    def setUp(self) -> None:
        self.parser = ObservationParser(self.card_database)

    def test_parse_deck_selection_observation(self) -> None:
        observation = self.parser.parse({"logs": [], "current": None, "select": None})
        self.assertIsNone(observation.state)
        self.assertIsNone(observation.selection)
        self.assertEqual(observation.logs, ())
        self.assertIsNone(observation.turn)
        self.assertFalse(observation.is_terminal)

    def test_parse_main_phase_observation(self) -> None:
        raw = self._build_main_observation(your_index=0)
        observation = self.parser.parse(raw)

        self.assertEqual(observation.turn, 3)
        self.assertEqual(observation.state.phase, GamePhase.MAIN)
        self.assertEqual(observation.me.player_index, 0)
        self.assertEqual(observation.opponent.player_index, 1)
        self.assertEqual(observation.me.active.name, "Lillie's Cutiefly")
        self.assertEqual(observation.me.active.card.metadata.card_id, 278)
        self.assertEqual(observation.me.active.attached_energy_types, (PokemonType.PSYCHIC,))
        self.assertEqual(observation.me.bench.max_size, 5)
        self.assertEqual(observation.selection.selection_type, SelectType.MAIN)
        self.assertEqual(observation.selection.context, SelectContext.MAIN)
        self.assertEqual(observation.selection.options[0].option_type, OptionType.END)
        self.assertEqual(observation.selection.options[1].option_type, OptionType.PLAY)
        self.assertEqual(observation.selection.options[1].zone, Zone.HAND)
        self.assertEqual(observation.selection.options[1].card.name, "Basic {G} Energy")
        self.assertEqual(len(observation.logs), 1)
        self.assertEqual(observation.logs[0].event_name, "TURN_START")

    def test_parse_perspective_flip_for_your_index_one(self) -> None:
        raw = self._build_main_observation(your_index=1)
        observation = self.parser.parse(raw)

        self.assertEqual(observation.me.player_index, 1)
        self.assertEqual(observation.opponent.player_index, 0)
        self.assertEqual(observation.me.side, PlayerSide.SELF)
        self.assertEqual(observation.opponent.side, PlayerSide.OPPONENT)
        self.assertEqual(observation.me.active.name, "Hippopotas")
        self.assertEqual(observation.opponent.active.name, "Lillie's Cutiefly")

    def test_parse_terminal_observation(self) -> None:
        raw = self._build_main_observation(your_index=0)
        raw["current"]["result"] = 0
        raw["logs"].append({"type": 23, "playerIndex": 0, "result": 0, "reason": 1})
        observation = self.parser.parse(raw)

        self.assertTrue(observation.is_terminal)
        self.assertEqual(observation.result, PlayerSide.SELF)
        self.assertEqual(observation.state.phase, GamePhase.FINISHED)
        self.assertEqual(observation.logs[-1].result_code, 0)
        self.assertEqual(observation.logs[-1].reason_code, 1)

    def test_parse_status_conditions_and_context_cards(self) -> None:
        raw = self._build_main_observation(your_index=0)
        raw["current"]["players"][0]["poisoned"] = True
        raw["current"]["players"][0]["confused"] = True
        raw["select"] = {
            "type": 1,
            "context": 8,
            "minCount": 1,
            "maxCount": 1,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "option": [
                {"type": 3, "cardId": 1, "serial": 2001, "playerIndex": 0, "area": 2, "index": 0}
            ],
            "deck": [{"id": 7, "serial": 2101, "playerIndex": 0}],
            "contextCard": {"id": 1126, "serial": 5001, "playerIndex": 0},
            "effect": {"id": 1126, "serial": 5001, "playerIndex": 0},
        }
        observation = self.parser.parse(raw)

        self.assertIn(StatusCondition.POISONED, observation.me.status_conditions)
        self.assertIn(StatusCondition.CONFUSED, observation.me.status_conditions)
        self.assertEqual(observation.selection.context, SelectContext.DISCARD)
        self.assertEqual(observation.selection.effect_context.context_card.name, "Precious Trolley")
        self.assertEqual(observation.selection.effect_context.source_card.name, "Precious Trolley")
        self.assertEqual(observation.selection.effect_context.exposed_deck_cards[0].name, "Basic {D} Energy")

    def test_unknown_optional_fields_are_ignored(self) -> None:
        raw = self._build_main_observation(your_index=0)
        raw["current"]["extraFutureField"] = {"x": 1}
        raw["current"]["players"][0]["futureFlag"] = True
        raw["select"]["option"][0]["futureOptionField"] = "x"
        raw["logs"][0]["futureLogField"] = 123
        observation = self.parser.parse(raw)

        self.assertEqual(observation.logs[0].metadata["futureLogField"], 123)
        self.assertEqual(observation.selection.options[0].metadata["futureOptionField"], "x")

    def test_missing_required_field_raises(self) -> None:
        raw = self._build_main_observation(your_index=0)
        del raw["current"]["players"]
        with self.assertRaises(MissingObservationFieldError):
            self.parser.parse(raw)

    def test_invalid_option_type_raises(self) -> None:
        raw = self._build_main_observation(your_index=0)
        raw["select"]["option"][0]["type"] = 999
        with self.assertRaises(InvalidObservationEnumError):
            self.parser.parse(raw)

    def test_unknown_card_id_raises(self) -> None:
        raw = self._build_main_observation(your_index=0)
        raw["current"]["players"][0]["active"][0]["id"] = 99999
        with self.assertRaises(MissingObservationCardError):
            self.parser.parse(raw)

    def test_invalid_player_count_raises(self) -> None:
        raw = self._build_main_observation(your_index=0)
        raw["current"]["players"] = raw["current"]["players"][:1]
        with self.assertRaises(CorruptedObservationError):
            self.parser.parse(raw)

    def _build_main_observation(self, *, your_index: int) -> dict[str, object]:
        player_zero = {
            "active": [
                {
                    "id": 278,
                    "serial": 1001,
                    "playerIndex": 0,
                    "hp": 30,
                    "maxHp": 30,
                    "appearThisTurn": False,
                    "energies": [5],
                    "energyCards": [{"id": 5, "serial": 3001, "playerIndex": 0}],
                    "tools": [],
                    "preEvolution": [],
                }
            ],
            "bench": [
                {
                    "id": 21,
                    "serial": 1002,
                    "playerIndex": 0,
                    "hp": 120,
                    "maxHp": 120,
                    "appearThisTurn": False,
                    "energies": [7],
                    "energyCards": [{"id": 7, "serial": 3002, "playerIndex": 0}],
                    "tools": [],
                    "preEvolution": [{"id": 278, "serial": 9001, "playerIndex": 0}],
                }
            ],
            "benchMax": 5,
            "deckCount": 45,
            "discard": [{"id": 1126, "serial": 5001, "playerIndex": 0}],
            "prize": [None, None, None, None, None, None],
            "handCount": 5,
            "hand": [{"id": 1, "serial": 2001, "playerIndex": 0}],
            "poisoned": False,
            "burned": False,
            "asleep": False,
            "paralyzed": False,
            "confused": False,
        }
        player_one = {
            "active": [
                {
                    "id": 22,
                    "serial": 1101,
                    "playerIndex": 1,
                    "hp": 70,
                    "maxHp": 70,
                    "appearThisTurn": False,
                    "energies": [6],
                    "energyCards": [{"id": 6, "serial": 3101, "playerIndex": 1}],
                    "tools": [],
                    "preEvolution": [],
                }
            ],
            "bench": [],
            "benchMax": 5,
            "deckCount": 44,
            "discard": [],
            "prize": [None, None, None, None, None, None],
            "handCount": 4,
            "hand": None,
            "poisoned": False,
            "burned": False,
            "asleep": False,
            "paralyzed": False,
            "confused": False,
        }
        return {
            "logs": [{"type": 2, "playerIndex": your_index}],
            "current": {
                "turn": 3,
                "turnActionCount": 1,
                "yourIndex": your_index,
                "firstPlayer": 0,
                "supporterPlayed": False,
                "stadiumPlayed": False,
                "energyAttached": True,
                "retreated": False,
                "result": -1,
                "stadium": [],
                "looking": None,
                "players": [player_zero, player_one],
            },
            "select": {
                "type": 0,
                "context": 0,
                "minCount": 1,
                "maxCount": 1,
                "remainDamageCounter": 0,
                "remainEnergyCost": 0,
                "option": [
                    {"type": 14},
                    {"type": 7, "cardId": 1, "serial": 2001, "playerIndex": 0, "area": 2, "index": 0},
                ],
                "deck": None,
                "contextCard": None,
                "effect": None,
            },
        }


if __name__ == "__main__":
    unittest.main()
