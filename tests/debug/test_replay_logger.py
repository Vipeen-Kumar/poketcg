"""Unit tests for replay and debug logging."""

from __future__ import annotations

import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
TMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from poketcg.actions import ActionFactory
from poketcg.cards import CardDatabase
from poketcg.debug import JsonReplayFormatter, MarkdownReplayFormatter, ReplayLogger
from poketcg.debug.models import DecisionMetadata, ReplaySession
from poketcg.debug.replay_logger import ReplayLoggerConfig
from poketcg.engine import ObservationParser


class ReplayLoggerTestCase(unittest.TestCase):
    """Tests for development replay logging."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.card_database = CardDatabase()
        cls.card_database.load()

    def setUp(self) -> None:
        self.parser = ObservationParser(self.card_database)
        self.action_factory = ActionFactory()

    def test_replay_creation_and_finish_writes_files(self) -> None:
        temp_dir = self._make_temp_dir()
        try:
            logger = ReplayLogger(
                ReplayLoggerConfig(
                    enabled=True,
                    output_directory=temp_dir,
                    markdown=True,
                    json=True,
                    maximum_saved_games=10,
                )
            )
            observation = self.parser.parse(self._build_observation())
            actions = self.action_factory.from_observation(observation)

            session = logger.start_game("game_001", metadata={"agent": "test"})
            self.assertIsNotNone(session)
            snapshot = logger.log_turn(
                observation,
                chosen_action=actions.actions[1],
                decision_metadata=DecisionMetadata(rule_name="CanAttack", reason="Enough energy attached.", notes="Debug replay"),
            )
            self.assertIsNotNone(snapshot)
            finished = logger.finish(metadata={"winner": "SELF"})

            self.assertIsNotNone(finished)
            self.assertEqual(finished.status, "finished")
            self.assertEqual(len(finished.turns), 1)
            self.assertTrue((temp_dir / "game_001.md").exists())
            self.assertTrue((temp_dir / "game_001.json").exists())

            payload = json.loads((temp_dir / "game_001.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["game_id"], "game_001")
            self.assertEqual(payload["turns"][0]["chosen_action"]["action_type"], "ATTACK")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_markdown_formatter_outputs_human_readable_sections(self) -> None:
        session = ReplaySession(game_id="game_002")
        session.start_game(started_at="2026-07-30T10:00:00Z")
        observation = self.parser.parse(self._build_observation())
        logger = ReplayLogger(ReplayLoggerConfig(enabled=True))
        logger._session = session
        logger.log_turn(observation, decision_metadata=DecisionMetadata(rule_name="InspectOnly", notes="No action chosen yet."))

        text = MarkdownReplayFormatter().format_session(session)
        self.assertIn("Turn 4", text)
        self.assertIn("Legal Actions", text)
        self.assertIn("Attack #1: Hold Still", text)
        self.assertIn("Rule: InspectOnly", text)

    def test_json_formatter_serializes_session(self) -> None:
        session = ReplaySession(game_id="game_003")
        session.start_game()
        observation = self.parser.parse(self._build_observation())
        logger = ReplayLogger(ReplayLoggerConfig(enabled=True))
        logger._session = session
        logger.log_turn(observation)

        payload = json.loads(JsonReplayFormatter().format_session(session))
        self.assertEqual(payload["game_id"], "game_003")
        self.assertEqual(payload["turns"][0]["legal_actions"][0]["action_type"], "END_TURN")

    def test_disabled_logging_is_noop(self) -> None:
        logger = ReplayLogger(ReplayLoggerConfig(enabled=False))
        observation = self.parser.parse(self._build_observation())

        self.assertIsNone(logger.start_game("game_004"))
        self.assertIsNone(logger.log_turn(observation))
        self.assertIsNone(logger.finish())
        self.assertIsNone(logger.session)

    def test_empty_turn_and_terminal_turn_are_supported(self) -> None:
        temp_dir = self._make_temp_dir()
        try:
            logger = ReplayLogger(
                ReplayLoggerConfig(
                    enabled=True,
                    output_directory=temp_dir,
                    markdown=False,
                    json=True,
                    maximum_saved_games=10,
                )
            )
            logger.start_game("game_005")

            setup_observation = self.parser.parse({"logs": [], "current": None, "select": None})
            empty_snapshot = logger.log_turn(setup_observation)
            self.assertIsNotNone(empty_snapshot)
            self.assertEqual(empty_snapshot.legal_actions, ())

            terminal_observation = self.parser.parse(self._build_terminal_observation())
            terminal_snapshot = logger.log_turn(terminal_observation)
            self.assertEqual(terminal_snapshot.result, "SELF")

            finished = logger.finish()
            self.assertEqual(len(finished.turns), 2)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _make_temp_dir(self) -> Path:
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        path = TMP_ROOT / f"debug_{uuid.uuid4().hex}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _build_observation(self) -> dict[str, object]:
        return {
            "logs": [{"type": 2, "playerIndex": 0}],
            "current": {
                "turn": 4,
                "turnActionCount": 0,
                "yourIndex": 0,
                "firstPlayer": 0,
                "supporterPlayed": False,
                "stadiumPlayed": False,
                "energyAttached": False,
                "retreated": False,
                "result": -1,
                "stadium": [{"id": 1242, "serial": 7001, "playerIndex": 0}],
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
                                "energies": [5],
                                "energyCards": [{"id": 5, "serial": 3001, "playerIndex": 0}],
                                "tools": [{"id": 1154, "serial": 4001, "playerIndex": 0}],
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
                        "deckCount": 42,
                        "discard": [{"id": 1126, "serial": 5001, "playerIndex": 0}],
                        "prize": [None, None, None, None],
                        "handCount": 4,
                        "hand": [
                            {"id": 1, "serial": 2001, "playerIndex": 0},
                            {"id": 1126, "serial": 2002, "playerIndex": 0},
                            {"id": 1181, "serial": 2003, "playerIndex": 0},
                            {"id": 1242, "serial": 2004, "playerIndex": 0},
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
                        "deckCount": 41,
                        "discard": [],
                        "prize": [None, None, None, None],
                        "handCount": 3,
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
                    {"type": 13, "attackId": 101},
                    {"type": 7, "cardId": 1126, "serial": 2002, "playerIndex": 0, "area": 2, "index": 1},
                ],
                "deck": None,
                "contextCard": None,
                "effect": None,
            },
        }

    def _build_terminal_observation(self) -> dict[str, object]:
        observation = self._build_observation()
        observation["current"]["result"] = 0
        observation["logs"].append({"type": 23, "playerIndex": 0, "result": 0, "reason": 1})
        return observation


if __name__ == "__main__":
    unittest.main()
