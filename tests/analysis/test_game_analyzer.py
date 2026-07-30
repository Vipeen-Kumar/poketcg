"""Unit tests for the game analysis API."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from poketcg.actions import ActionFactory, AttackAction, EndTurnAction, PlayCardAction
from poketcg.analysis import GameAnalyzer
from poketcg.cards import CardDatabase
from poketcg.domain import PlayerSide, StatusCondition
from poketcg.engine import ObservationParser


class GameAnalyzerTestCase(unittest.TestCase):
    """Tests for factual game-state queries."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.card_database = CardDatabase()
        cls.card_database.load()

    def setUp(self) -> None:
        self.parser = ObservationParser(self.card_database)
        self.action_factory = ActionFactory()

    def test_main_observation_queries(self) -> None:
        analyzer = GameAnalyzer(self.parser.parse(self._build_main_observation()))

        self.assertFalse(analyzer.is_terminal())
        self.assertEqual(analyzer.current_turn(), 3)
        self.assertEqual(analyzer.current_player(), PlayerSide.SELF)
        self.assertEqual(analyzer.first_player(), PlayerSide.SELF)
        self.assertEqual(analyzer.active().name, "Lillie's Cutiefly")
        self.assertEqual(len(analyzer.bench()), 1)
        self.assertEqual(analyzer.deck_size(), 45)
        self.assertEqual(len(analyzer.discard()), 2)
        self.assertEqual(analyzer.prizes_remaining(), 6)
        self.assertEqual(analyzer.bench_space(), 4)
        self.assertTrue(analyzer.has_empty_bench_slot())
        self.assertEqual(analyzer.damage_taken(), 10)
        self.assertEqual(analyzer.hp_remaining(), 20)
        self.assertFalse(analyzer.has_energy())
        self.assertEqual(analyzer.energy_count(), 2)
        self.assertFalse(analyzer.has_tool(analyzer.active()))
        self.assertFalse(analyzer.is_knocked_out())
        self.assertTrue(analyzer.has_status_condition())
        self.assertTrue(analyzer.is_poisoned())
        self.assertFalse(analyzer.is_asleep())
        self.assertEqual(analyzer.attack_names(), ("Hold Still",))
        self.assertEqual(analyzer.attack_count(), 1)
        self.assertEqual(len(analyzer.attack_cost(0)), 1)
        self.assertIsNone(analyzer.attack_damage("Hold Still"))
        self.assertTrue(analyzer.has_supporter())
        self.assertTrue(analyzer.has_item())
        self.assertTrue(analyzer.has_stadium())
        self.assertTrue(analyzer.has_tool())
        self.assertEqual(len(analyzer.basic_pokemon_in_hand()), 1)
        self.assertEqual(len(analyzer.energy_cards_in_hand()), 1)
        self.assertEqual(len(analyzer.search_cards("rocket")), 1)
        self.assertEqual(analyzer.total_energy(), 2)
        self.assertEqual(analyzer.total_hp(), 140)
        self.assertEqual(analyzer.total_damage(), 10)
        self.assertEqual(analyzer.total_prizes(), 6)
        self.assertEqual(analyzer.pokemon_count(), 2)
        self.assertEqual(analyzer.supporter_count(), 1)
        self.assertEqual(analyzer.trainer_count(), 4)

    def test_legal_action_queries(self) -> None:
        observation = self.parser.parse(self._build_main_observation())
        analyzer = GameAnalyzer(observation)

        self.assertEqual(len(analyzer.actions()), 3)
        self.assertTrue(all(isinstance(action, (EndTurnAction, PlayCardAction, AttackAction)) for action in analyzer.actions()))
        self.assertEqual(len(analyzer.attack_actions()), 1)
        self.assertEqual(len(analyzer.play_actions()), 1)
        self.assertEqual(len(analyzer.energy_actions()), 0)
        self.assertEqual(len(analyzer.retreat_actions()), 0)
        self.assertEqual(len(analyzer.evolution_actions()), 0)
        self.assertEqual(len(analyzer.ability_actions()), 0)
        self.assertIsInstance(analyzer.end_turn_action(), EndTurnAction)
        self.assertTrue(analyzer.can_attack())
        self.assertFalse(analyzer.can_retreat())
        self.assertFalse(analyzer.can_evolve())

    def test_terminal_observation_queries(self) -> None:
        raw = self._build_main_observation()
        raw["current"]["result"] = 0
        observation = self.parser.parse(raw)
        analyzer = GameAnalyzer(observation)

        self.assertTrue(analyzer.is_terminal())
        self.assertEqual(analyzer.total_prizes(PlayerSide.OPPONENT), 6)

    def test_setup_observation_with_no_state(self) -> None:
        observation = self.parser.parse({"logs": [], "current": None, "select": None})
        analyzer = GameAnalyzer(observation)

        self.assertIsNone(analyzer.current_turn())
        self.assertIsNone(analyzer.current_player())
        self.assertEqual(analyzer.actions(), ())
        self.assertEqual(analyzer.hand(), ())
        self.assertEqual(analyzer.bench(), ())
        self.assertEqual(analyzer.bench_pokemon(), ())
        self.assertEqual(analyzer.total_hp(), 0)

    def test_empty_bench_and_no_active(self) -> None:
        analyzer = GameAnalyzer(self.parser.parse(self._build_no_active_observation()))

        self.assertIsNone(analyzer.active())
        self.assertEqual(analyzer.bench_pokemon(), ())
        self.assertEqual(analyzer.pokemon_count(), 0)
        self.assertFalse(analyzer.can_attack())
        self.assertFalse(analyzer.can_retreat())
        self.assertFalse(analyzer.has_special_condition())

    def test_opponent_hidden_hand_queries(self) -> None:
        analyzer = GameAnalyzer(self.parser.parse(self._build_main_observation()))

        self.assertEqual(analyzer.hand(PlayerSide.OPPONENT), ())
        self.assertEqual(analyzer.deck_size(PlayerSide.OPPONENT), 44)
        self.assertFalse(analyzer.has_supporter(PlayerSide.OPPONENT))

    def test_cached_action_batch_can_be_injected(self) -> None:
        observation = self.parser.parse(self._build_main_observation())
        action_batch = self.action_factory.from_observation(observation)
        analyzer = GameAnalyzer(observation, actions=action_batch)

        self.assertEqual(tuple(type(action) for action in analyzer.actions()), tuple(type(action) for action in action_batch.actions))

    def _build_main_observation(self) -> dict[str, object]:
        return {
            "logs": [{"type": 2, "playerIndex": 0}],
            "current": {
                "turn": 3,
                "turnActionCount": 1,
                "yourIndex": 0,
                "firstPlayer": 0,
                "supporterPlayed": True,
                "stadiumPlayed": False,
                "energyAttached": False,
                "retreated": False,
                "result": -1,
                "stadium": [{"id": 1154, "serial": 7001, "playerIndex": 0}],
                "looking": None,
                "players": [
                    {
                        "active": [
                            {
                                "id": 278,
                                "serial": 1001,
                                "playerIndex": 0,
                                "hp": 20,
                                "maxHp": 30,
                                "appearThisTurn": False,
                                "energies": [],
                                "energyCards": [],
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
                                "energies": [7, 0],
                                "energyCards": [{"id": 7, "serial": 3002, "playerIndex": 0}],
                                "tools": [],
                                "preEvolution": [{"id": 278, "serial": 9001, "playerIndex": 0}],
                            }
                        ],
                        "benchMax": 5,
                        "deckCount": 45,
                        "discard": [
                            {"id": 1126, "serial": 5001, "playerIndex": 0},
                            {"id": 11, "serial": 5002, "playerIndex": 0},
                        ],
                        "prize": [None, None, None, None, None, None],
                        "handCount": 6,
                        "hand": [
                            {"id": 1, "serial": 2001, "playerIndex": 0},
                            {"id": 1126, "serial": 2002, "playerIndex": 0},
                            {"id": 1242, "serial": 2003, "playerIndex": 0},
                            {"id": 1154, "serial": 2004, "playerIndex": 0},
                            {"id": 1181, "serial": 2005, "playerIndex": 0},
                            {"id": 278, "serial": 2006, "playerIndex": 0},
                        ],
                        "poisoned": True,
                        "burned": False,
                        "asleep": False,
                        "paralyzed": False,
                        "confused": False,
                    },
                    {
                        "active": [
                            {
                                "id": 22,
                                "serial": 1101,
                                "playerIndex": 1,
                                "hp": 60,
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
                    },
                ],
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
                    {"type": 7, "cardId": 1126, "serial": 2002, "playerIndex": 0, "area": 2, "index": 1},
                    {"type": 13, "attackId": 101},
                ],
                "deck": None,
                "contextCard": None,
                "effect": None,
            },
        }

    def _build_no_active_observation(self) -> dict[str, object]:
        return {
            "logs": [],
            "current": {
                "turn": 0,
                "turnActionCount": 0,
                "yourIndex": 0,
                "firstPlayer": -1,
                "supporterPlayed": False,
                "stadiumPlayed": False,
                "energyAttached": False,
                "retreated": False,
                "result": -1,
                "stadium": [],
                "looking": None,
                "players": [
                    {
                        "active": [],
                        "bench": [],
                        "benchMax": 5,
                        "deckCount": 60,
                        "discard": [],
                        "prize": [None, None, None, None, None, None],
                        "handCount": 7,
                        "hand": [{"id": 278, "serial": 2005, "playerIndex": 0}],
                        "poisoned": False,
                        "burned": False,
                        "asleep": False,
                        "paralyzed": False,
                        "confused": False,
                    },
                    {
                        "active": [],
                        "bench": [],
                        "benchMax": 5,
                        "deckCount": 60,
                        "discard": [],
                        "prize": [None, None, None, None, None, None],
                        "handCount": 7,
                        "hand": None,
                        "poisoned": False,
                        "burned": False,
                        "asleep": False,
                        "paralyzed": False,
                        "confused": False,
                    },
                ],
            },
            "select": None,
        }


if __name__ == "__main__":
    unittest.main()
