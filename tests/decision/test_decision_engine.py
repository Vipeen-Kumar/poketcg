"""Unit tests for the deterministic decision engine."""

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

from poketcg.actions import ActionFactory, EndTurnAction, PlayCardAction
from poketcg.analysis import GameAnalyzer
from poketcg.cards import CardDatabase
from poketcg.decision import (
    BaseRule,
    CircularPriorityError,
    DecisionConfigurationError,
    DecisionContext,
    DecisionEngine,
    DecisionEngineConfig,
    DecisionTrace,
    DuplicateRuleNameError,
    EmptyLegalActionError,
    FirstLegalActionRule,
    FallbackRule,
    MissingFallbackRuleError,
    RuleRegistry,
    RuleResult,
    UnknownRuleError,
)
from poketcg.debug import ReplayLogger
from poketcg.debug.replay_logger import ReplayLoggerConfig
from poketcg.engine import ObservationParser


class DecisionEngineTestCase(unittest.TestCase):
    """Tests for deterministic rule execution and trace capture."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.card_database = CardDatabase()
        cls.card_database.load()

    def setUp(self) -> None:
        self.parser = ObservationParser(self.card_database)
        self.action_factory = ActionFactory()

    def test_registry_orders_by_priority(self) -> None:
        registry = RuleRegistry([self._build_low_priority_rule(), self._build_high_priority_rule()])

        ordered = registry.ordered_rules()

        self.assertEqual([rule.name for rule in ordered], ["HighPriorityRule", "LowPriorityRule"])

    def test_duplicate_registration_is_rejected(self) -> None:
        registry = RuleRegistry()
        rule = self._build_duplicate_rule()

        registry.register(rule)
        with self.assertRaises(DuplicateRuleNameError):
            registry.register(rule)

    def test_circular_priority_detection(self) -> None:
        registry = RuleRegistry([self._build_cycle_rule_a(), self._build_cycle_rule_b()])

        with self.assertRaises(CircularPriorityError):
            registry.ordered_rules()

    def test_default_rule_order_prefers_end_turn(self) -> None:
        observation = self.parser.parse(self._build_observation())
        context = DecisionContext(analyzer=GameAnalyzer(observation))

        engine = DecisionEngine()
        action = engine.choose_action(context)

        self.assertIsInstance(action, EndTurnAction)
        self.assertIsNotNone(engine.last_outcome)
        self.assertEqual(engine.last_outcome.trace.selected_rule_name, "AlwaysEndTurnRule")

    def test_disabled_rules_allow_first_legal_action(self) -> None:
        observation = self.parser.parse(self._build_observation())
        context = DecisionContext(
            analyzer=GameAnalyzer(observation),
            config=DecisionEngineConfig(disabled_rules=("AlwaysEndTurnRule",)),
        )

        engine = DecisionEngine()
        action = engine.choose_action(context)

        self.assertIsInstance(action, EndTurnAction)
        self.assertEqual(engine.last_outcome.trace.selected_rule_name, "FirstLegalActionRule")
        self.assertEqual([result.rule_name for result in engine.last_outcome.trace.rule_results], ["FirstLegalActionRule"])

    def test_fallback_uses_end_turn_when_all_rules_disabled(self) -> None:
        observation = self.parser.parse(self._build_observation())
        context = DecisionContext(
            analyzer=GameAnalyzer(observation),
            config=DecisionEngineConfig(enabled_rules=()),
        )

        engine = DecisionEngine()
        action = engine.choose_action(context)

        self.assertIsInstance(action, EndTurnAction)
        self.assertTrue(engine.last_outcome.trace.fallback_used)
        self.assertEqual(engine.last_outcome.trace.selected_rule_name, "FallbackRule")

    def test_empty_legal_actions_raise(self) -> None:
        observation = self.parser.parse({"logs": [], "current": None, "select": None})
        context = DecisionContext(analyzer=GameAnalyzer(observation), legal_actions=())

        with self.assertRaises(EmptyLegalActionError):
            DecisionEngine().choose_action(context)

    def test_missing_fallback_rule_raises(self) -> None:
        class FailingRule(BaseRule):
            auto_register = False
            default_priority = 1

            def applies(self, context: DecisionContext) -> bool:
                return True

            def evaluate(self, context: DecisionContext) -> RuleResult:
                return self._result(passed=False, action=None, reason="No selection")

        registry = RuleRegistry([FailingRule()])
        observation = self.parser.parse(self._build_observation())
        context = DecisionContext(
            analyzer=GameAnalyzer(observation),
            config=DecisionEngineConfig(enabled_rules=("FailingRule",)),
        )

        with self.assertRaises(MissingFallbackRuleError):
            DecisionEngine(registry=registry).choose_action(context)

    def test_unknown_enabled_rule_raises_in_strict_mode(self) -> None:
        observation = self.parser.parse(self._build_observation())
        context = DecisionContext(
            analyzer=GameAnalyzer(observation),
            config=DecisionEngineConfig(enabled_rules=("MissingRule",)),
        )

        with self.assertRaises(UnknownRuleError):
            DecisionEngine().choose_action(context)

    def test_trace_serialization_and_replay_logger_integration(self) -> None:
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
            logger.start_game("decision_001")

            observation = self.parser.parse(self._build_observation())
            class FailingRule(BaseRule):
                auto_register = False
                default_priority = 400

                def applies(self, context: DecisionContext) -> bool:
                    return True

                def evaluate(self, context: DecisionContext) -> RuleResult:
                    return self._result(passed=False, action=None, reason="Trace probe")

            registry = RuleRegistry([FailingRule(), FirstLegalActionRule()])
            context = DecisionContext(
                analyzer=GameAnalyzer(observation),
                config=DecisionEngineConfig(logging_enabled=True),
                replay_logger=logger,
            )

            engine = DecisionEngine(registry=registry)
            action = engine.choose_action(context)

            self.assertIsInstance(action, EndTurnAction)
            self.assertIsInstance(engine.last_outcome.trace, DecisionTrace)
            self.assertEqual(engine.last_outcome.trace.selected_rule_name, "FirstLegalActionRule")

            trace_payload = engine.last_outcome.trace.to_dict()
            json.dumps(trace_payload)
            self.assertEqual(trace_payload["rule_results"][0]["rule_name"], "FailingRule")
            self.assertEqual(trace_payload["rule_results"][1]["rule_name"], "FirstLegalActionRule")

            finished = logger.finish()
            self.assertIsNotNone(finished)
            self.assertTrue((temp_dir / "decision_001.md").exists())
            self.assertTrue((temp_dir / "decision_001.json").exists())

            snapshot = logger.session.turns[0]
            self.assertIsNotNone(snapshot.decision_trace)
            self.assertEqual(snapshot.decision_trace["selected_rule_name"], "FirstLegalActionRule")
            self.assertEqual(snapshot.decision_metadata.rule_name, "FirstLegalActionRule")
            self.assertEqual(snapshot.decision_metadata.reason, "Selected the first legal action.")

            payload = json.loads((temp_dir / "decision_001.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["turns"][0]["decision_trace"]["selected_rule_name"], "FirstLegalActionRule")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_context_state_mismatch_raises(self) -> None:
        observation = self.parser.parse(self._build_observation())
        mismatched_state = observation.state.__class__()

        with self.assertRaises(DecisionConfigurationError):
            DecisionContext(analyzer=GameAnalyzer(observation), game_state=mismatched_state)

    def _make_temp_dir(self) -> Path:
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        path = TMP_ROOT / f"decision_{uuid.uuid4().hex}"
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
                "stadium": [],
                "looking": None,
                "players": [
                    {
                        "active": [{"id": 278, "serial": 1001, "playerIndex": 0, "hp": 20, "maxHp": 30, "appearThisTurn": False, "energies": [5], "energyCards": [{"id": 5, "serial": 3001, "playerIndex": 0}], "tools": [], "preEvolution": []}],
                        "bench": [],
                        "benchMax": 5,
                        "deckCount": 42,
                        "discard": [],
                        "prize": [None, None, None, None, None, None],
                        "handCount": 4,
                        "hand": [
                            {"id": 1126, "serial": 2002, "playerIndex": 0},
                            {"id": 1, "serial": 2001, "playerIndex": 0},
                        ],
                        "poisoned": False,
                        "burned": False,
                        "asleep": False,
                        "paralyzed": False,
                        "confused": False,
                    },
                    {
                        "active": [None],
                        "bench": [],
                        "benchMax": 5,
                        "deckCount": 41,
                        "discard": [],
                        "prize": [None, None, None, None, None, None],
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
                    {"type": 7, "cardId": 1126, "serial": 2002, "playerIndex": 0, "area": 2, "index": 0},
                ],
                "deck": None,
                "contextCard": None,
                "effect": None,
            },
        }

    def _build_low_priority_rule(self) -> BaseRule:
        class LowPriorityRule(BaseRule):
            auto_register = False
            default_priority = 5

            def applies(self, context: DecisionContext) -> bool:
                return True

            def evaluate(self, context: DecisionContext) -> RuleResult:
                return self._result(passed=True, action=None, reason="Low priority")

        return LowPriorityRule()

    def _build_high_priority_rule(self) -> BaseRule:
        class HighPriorityRule(BaseRule):
            auto_register = False
            default_priority = 25

            def applies(self, context: DecisionContext) -> bool:
                return True

            def evaluate(self, context: DecisionContext) -> RuleResult:
                return self._result(passed=True, action=None, reason="High priority")

        return HighPriorityRule()

    def _build_duplicate_rule(self) -> BaseRule:
        class DuplicateRule(BaseRule):
            auto_register = False
            default_priority = 1

            def applies(self, context: DecisionContext) -> bool:
                return True

            def evaluate(self, context: DecisionContext) -> RuleResult:
                return self._result(passed=True, action=None, reason="duplicate")

        return DuplicateRule()

    def _build_cycle_rule_a(self) -> BaseRule:
        class RuleA(BaseRule):
            auto_register = False
            default_priority = 10
            runs_after = ("RuleB",)

            def applies(self, context: DecisionContext) -> bool:
                return True

            def evaluate(self, context: DecisionContext) -> RuleResult:
                return self._result(passed=True, action=None, reason="A")

        return RuleA()

    def _build_cycle_rule_b(self) -> BaseRule:
        class RuleB(BaseRule):
            auto_register = False
            default_priority = 10
            runs_after = ("RuleA",)

            def applies(self, context: DecisionContext) -> bool:
                return True

            def evaluate(self, context: DecisionContext) -> RuleResult:
                return self._result(passed=True, action=None, reason="B")

        return RuleB()


if __name__ == "__main__":
    unittest.main()