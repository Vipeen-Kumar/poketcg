"""Integration smoke tests for the baseline agent submission pipeline."""

from __future__ import annotations

import shutil
import sys
import unittest
import uuid
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
TMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from poketcg.agent import BaselineAgentConfig, create_baseline_agent
from poketcg.debug.replay_logger import ReplayLoggerConfig


class BaselinePipelineIntegrationTestCase(unittest.TestCase):
    """Exercise the full raw-observation baseline pipeline."""

    def test_raw_observation_to_submission_indices(self) -> None:
        temp_dir = self._make_temp_dir()
        try:
            agent = create_baseline_agent(
                BaselineAgentConfig(
                    replay=ReplayLoggerConfig(
                        enabled=True,
                        output_directory=temp_dir,
                        markdown=True,
                        json=True,
                        maximum_saved_games=10,
                    )
                )
            )

            deck_payload = agent({"logs": [], "current": None, "select": None})
            action_payload = agent(self._build_attack_observation())

            self.assertEqual(len(deck_payload), 60)
            self.assertEqual(action_payload, [1])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _make_temp_dir(self) -> Path:
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        path = TMP_ROOT / f"integration_{uuid.uuid4().hex}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _build_attack_observation(self) -> dict[str, object]:
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
                "stadium": [],
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
                                "tools": [],
                                "preEvolution": [],
                            }
                        ],
                        "bench": [],
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
                        "poisoned": False,
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


if __name__ == "__main__":
    unittest.main()
