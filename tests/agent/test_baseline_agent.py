"""Integration tests for the baseline agent pipeline."""

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
from poketcg.agent import BaselineAgent, BaselineAgentConfig, create_baseline_agent
from poketcg.cards import CardDatabase
from poketcg.decision import DecisionContext, DecisionEngine
from poketcg.engine import ObservationParser


class BrokenDecisionEngine(DecisionEngine):
    """Decision engine stub that always fails."""

    def decide(self, context: DecisionContext):
        raise RuntimeError("forced decision failure")


class BaselineAgentTestCase(unittest.TestCase):
    """Tests for the end-to-end baseline agent orchestration."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.card_database = CardDatabase()
        cls.card_database.load()

    def test_select_deck_is_deterministic_and_valid(self) -> None:
        agent = create_baseline_agent(BaselineAgentConfig(replay=self._replay_config(enabled=False)))

        first = agent.select_deck()
        second = agent.select_deck()

        self.assertEqual(first.card_ids, second.card_ids)
        self.assertEqual(len(first.card_ids), 60)
        self.assertGreaterEqual(len(set(first.card_ids)), 5)

    def test_deck_selection_payload_returns_deck_list(self) -> None:
        agent = create_baseline_agent(BaselineAgentConfig(replay=self._replay_config(enabled=False)))

        response = agent.handle_observation({"logs": [], "current": None, "select": None})

        self.assertEqual(len(response), 60)

    def test_gameplay_pipeline_returns_legal_index_and_logs_replay(self) -> None:
        temp_dir = self._make_temp_dir()
        try:
            agent = create_baseline_agent(BaselineAgentConfig(replay=self._replay_config(output_directory=temp_dir)))
            agent.handle_observation({"logs": [], "current": None, "select": None})

            response = agent.handle_observation(self._build_attack_observation())

            self.assertEqual(response, [1])
            session = agent.replay_logger.session
            self.assertIsNotNone(session)
            self.assertEqual(len(session.turns), 1)
            self.assertIsNotNone(session.turns[0].decision_trace)
            self.assertEqual(session.turns[0].decision_metadata.rule_name, "AttackRule")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_terminal_observation_finishes_replay(self) -> None:
        temp_dir = self._make_temp_dir()
        try:
            agent = create_baseline_agent(BaselineAgentConfig(replay=self._replay_config(output_directory=temp_dir)))
            agent.handle_observation({"logs": [], "current": None, "select": None})

            response = agent.handle_observation(self._build_terminal_observation())

            self.assertEqual(response, [1])
            session = agent.replay_logger.session
            self.assertIsNotNone(session)
            self.assertEqual(session.status, "finished")
            self.assertTrue((temp_dir / "game_001.json").exists())
            payload = json.loads((temp_dir / "game_001.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["metadata"]["result"], "SELF")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_engine_failure_uses_safe_fallback(self) -> None:
        temp_dir = self._make_temp_dir()
        try:
            parser = ObservationParser(self.card_database)
            action_factory = ActionFactory()
            replay_config = self._replay_config(output_directory=temp_dir)
            from poketcg.debug import ReplayLogger

            agent = BaselineAgent(
                config=BaselineAgentConfig(replay=replay_config),
                card_database=self.card_database,
                observation_parser=parser,
                action_factory=action_factory,
                decision_engine=BrokenDecisionEngine(),
                replay_logger=ReplayLogger(replay_config, action_factory=action_factory),
            )
            agent.handle_observation({"logs": [], "current": None, "select": None})

            response = agent.handle_observation(self._build_attack_observation())

            self.assertEqual(response, [0])
            session = agent.replay_logger.session
            self.assertIsNotNone(session)
            self.assertEqual(session.turns[0].decision_metadata.rule_name, "FallbackRule")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_validation_rejects_action_with_invalid_index(self) -> None:
        """Test that actions with out-of-range indices fall back to first legal action."""
        observation = ObservationParser(self.card_database).parse(self._build_attack_observation())
        agent = create_baseline_agent(BaselineAgentConfig(replay=self._replay_config(enabled=False)))
        artifacts = agent._build_decision_artifacts(observation)

        # Create an action with invalid index
        from poketcg.actions import EndTurnAction, ActionKind
        from poketcg.domain import SelectContext, SelectType, OptionReference, OptionType

        invalid_action = EndTurnAction(
            action_index=999,  # Out of range
            kind=ActionKind.END_TURN,
            option=OptionReference(option_type=OptionType.END),
            selection_context=SelectContext.MAIN,
            selection_type=SelectType.MAIN,
        )

        validated = agent._validate_action_legality(invalid_action, artifacts)

        # Should fall back to first legal action
        self.assertEqual(validated.action_index, 0)
        self.assertIn(validated, artifacts.context.legal_actions)

    def test_validation_rejects_none_action(self) -> None:
        """Test that None actions fall back to first legal action."""
        observation = ObservationParser(self.card_database).parse(self._build_attack_observation())
        agent = create_baseline_agent(BaselineAgentConfig(replay=self._replay_config(enabled=False)))
        artifacts = agent._build_decision_artifacts(observation)

        validated = agent._validate_action_legality(None, artifacts)

        # Should fall back to first legal action
        self.assertEqual(validated.action_index, 0)
        self.assertIn(validated, artifacts.context.legal_actions)

    def test_validation_accepts_legal_action(self) -> None:
        """Test that legal actions are accepted without modification."""
        observation = ObservationParser(self.card_database).parse(self._build_attack_observation())
        agent = create_baseline_agent(BaselineAgentConfig(replay=self._replay_config(enabled=False)))
        artifacts = agent._build_decision_artifacts(observation)

        # Use first legal action
        legal_action = artifacts.context.legal_actions[0]
        validated = agent._validate_action_legality(legal_action, artifacts)

        # Should be the same action
        self.assertIs(validated, legal_action)

    def _replay_config(self, *, enabled: bool = True, output_directory: Path | None = None):
        from poketcg.debug.replay_logger import ReplayLoggerConfig

        return ReplayLoggerConfig(
            enabled=enabled,
            output_directory=output_directory or Path("outputs/replays"),
            markdown=True,
            json=True,
            maximum_saved_games=10,
        )

    def _make_temp_dir(self) -> Path:
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        path = TMP_ROOT / f"agent_{uuid.uuid4().hex}"
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

    def _build_terminal_observation(self) -> dict[str, object]:
        observation = self._build_attack_observation()
        observation["current"]["result"] = 0
        observation["logs"].append({"type": 23, "playerIndex": 0, "result": 0, "reason": 1})
        return observation


if __name__ == "__main__":
    unittest.main()
