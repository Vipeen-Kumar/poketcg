"""Unit tests for the deterministic decision engine."""

from __future__ import annotations

import json
import shutil
import sys
import unittest
import uuid
from dataclasses import dataclass
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
TMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from poketcg.actions import ActionKind, BaseAction, EndTurnAction
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
    MissingFallbackRuleError,
    RuleRegistry,
    RuleResult,
    UnknownRuleError,
)
from poketcg.debug import ReplayLogger
from poketcg.debug.replay_logger import ReplayLoggerConfig
from poketcg.domain import Observation, OptionReference, OptionType, SelectContext, SelectType


@dataclass(slots=True)
class StubAnalyzer:
    """Minimal analyzer stub for engine-only tests."""

    legal_actions: tuple[BaseAction, ...]
    observation: Observation
    state: object | None = None

    def actions(self) -> tuple[BaseAction, ...]:
        return self.legal_actions

    def current_turn(self) -> int | None:
        return None

    def current_player(self):
        return None

    def me(self):
        return None

    def opponent(self):
        return None


class DecisionEngineTestCase(unittest.TestCase):
    """Tests for deterministic rule execution and trace capture."""

    def test_registry_orders_by_priority(self) -> None:
        registry = RuleRegistry([self._low_priority_rule(), self._high_priority_rule()])

        ordered = registry.ordered_rules()

        self.assertEqual([rule.name for rule in ordered], ["HighPriorityRule", "LowPriorityRule"])

    def test_duplicate_registration_is_rejected(self) -> None:
        registry = RuleRegistry()
        rule = self._duplicate_rule()

        registry.register(rule)
        with self.assertRaises(DuplicateRuleNameError):
            registry.register(rule)

    def test_circular_priority_detection(self) -> None:
        registry = RuleRegistry([self._cycle_rule_a(), self._cycle_rule_b()])

        with self.assertRaises(CircularPriorityError):
            registry.ordered_rules()

    def test_disabled_rules_allow_second_rule(self) -> None:
        action = self._make_action()
        rules = [self._failing_rule(), self._passing_rule(action)]
        context = self._build_context(rules, disabled_rules=("FailingRule",))

        engine = DecisionEngine(registry=RuleRegistry(rules))
        chosen_action = engine.choose_action(context)

        self.assertIs(chosen_action, action)
        self.assertEqual(engine.last_outcome.trace.selected_rule_name, "PassingRule")
        self.assertEqual([result.rule_name for result in engine.last_outcome.trace.rule_results], ["PassingRule"])

    def test_fallback_uses_first_legal_action_when_all_rules_fail(self) -> None:
        action = self._make_action()
        fallback = self._fallback_rule()
        rules = [self._failing_rule(), fallback]
        context = self._build_context(rules, legal_actions=(action,))

        engine = DecisionEngine(registry=RuleRegistry(rules))
        chosen_action = engine.choose_action(context)

        self.assertIs(chosen_action, action)
        self.assertTrue(engine.last_outcome.trace.fallback_used)
        self.assertEqual(engine.last_outcome.trace.selected_rule_name, "FallbackRule")

    def test_empty_legal_actions_raise(self) -> None:
        rules = [self._failing_rule()]
        context = self._build_context(rules, legal_actions=())

        with self.assertRaises(EmptyLegalActionError):
            DecisionEngine(registry=RuleRegistry(rules)).choose_action(context)

    def test_missing_fallback_rule_raises(self) -> None:
        rules = [self._failing_rule()]
        context = self._build_context(rules, legal_actions=(self._make_action(),))

        with self.assertRaises(MissingFallbackRuleError):
            DecisionEngine(registry=RuleRegistry(rules)).choose_action(context)

    def test_unknown_enabled_rule_raises_in_strict_mode(self) -> None:
        rules = [self._failing_rule()]
        context = self._build_context(
            rules,
            config=DecisionEngineConfig(enabled_rules=("MissingRule",)),
        )

        with self.assertRaises(UnknownRuleError):
            DecisionEngine(registry=RuleRegistry(rules)).choose_action(context)

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

            action = self._make_action()
            rules = [self._failing_rule(), self._passing_rule(action)]
            context = self._build_context(
                rules,
                legal_actions=(action,),
                config=DecisionEngineConfig(logging_enabled=True),
                replay_logger=logger,
            )

            engine = DecisionEngine(registry=RuleRegistry(rules))
            chosen_action = engine.choose_action(context)

            self.assertIs(chosen_action, action)
            self.assertIsInstance(engine.last_outcome.trace, DecisionTrace)
            self.assertEqual(engine.last_outcome.trace.selected_rule_name, "PassingRule")

            trace_payload = engine.last_outcome.trace.to_dict()
            json.dumps(trace_payload)
            self.assertEqual(trace_payload["rule_results"][0]["rule_name"], "FailingRule")
            self.assertEqual(trace_payload["rule_results"][1]["rule_name"], "PassingRule")

            finished = logger.finish()
            self.assertIsNotNone(finished)
            self.assertTrue((temp_dir / "decision_001.md").exists())
            self.assertTrue((temp_dir / "decision_001.json").exists())

            snapshot = logger.session.turns[0]
            self.assertIsNotNone(snapshot.decision_trace)
            self.assertEqual(snapshot.decision_trace["selected_rule_name"], "PassingRule")
            self.assertEqual(snapshot.decision_metadata.rule_name, "PassingRule")
            self.assertEqual(snapshot.decision_metadata.reason, "Passing rule passed.")

            payload = json.loads((temp_dir / "decision_001.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["turns"][0]["decision_trace"]["selected_rule_name"], "PassingRule")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_context_state_mismatch_raises(self) -> None:
        analyzer = StubAnalyzer(
            legal_actions=(self._make_action(),),
            observation=self._build_observation(),
            state=object(),
        )

        with self.assertRaises(DecisionConfigurationError):
            DecisionContext(analyzer=analyzer, game_state=object())

    def _build_context(
        self,
        rules: list[BaseRule],
        *,
        legal_actions: tuple[BaseAction, ...] | None = None,
        config: DecisionEngineConfig | None = None,
        disabled_rules: tuple[str, ...] = (),
        replay_logger: ReplayLogger | None = None,
    ) -> DecisionContext:
        action_set = legal_actions if legal_actions is not None else (self._make_action(),)
        observation = self._build_observation()
        analyzer = StubAnalyzer(legal_actions=action_set, observation=observation)
        resolved_config = config or DecisionEngineConfig(disabled_rules=disabled_rules)
        return DecisionContext(analyzer=analyzer, legal_actions=action_set, config=resolved_config, replay_logger=replay_logger)

    def _build_observation(self) -> Observation:
        return Observation(state=None, logs=(), selection=None)

    def _make_action(self) -> BaseAction:
        option = OptionReference(option_type=OptionType.END)
        return EndTurnAction(
            action_index=0,
            kind=ActionKind.END_TURN,
            option=option,
            selection_context=SelectContext.MAIN,
            selection_type=SelectType.MAIN,
        )

    def _low_priority_rule(self) -> BaseRule:
        class LowPriorityRule(BaseRule):
            auto_register = False
            default_priority = 5

            def applies(self, context: DecisionContext) -> bool:
                return True

            def evaluate(self, context: DecisionContext) -> RuleResult:
                return self._result(passed=True, action=None, reason="Low priority")

        return LowPriorityRule()

    def _high_priority_rule(self) -> BaseRule:
        class HighPriorityRule(BaseRule):
            auto_register = False
            default_priority = 25

            def applies(self, context: DecisionContext) -> bool:
                return True

            def evaluate(self, context: DecisionContext) -> RuleResult:
                return self._result(passed=True, action=None, reason="High priority")

        return HighPriorityRule()

    def _duplicate_rule(self) -> BaseRule:
        class DuplicateRule(BaseRule):
            auto_register = False
            default_priority = 1

            def applies(self, context: DecisionContext) -> bool:
                return True

            def evaluate(self, context: DecisionContext) -> RuleResult:
                return self._result(passed=True, action=None, reason="duplicate")

        return DuplicateRule()

    def _cycle_rule_a(self) -> BaseRule:
        class RuleA(BaseRule):
            auto_register = False
            default_priority = 10
            runs_after = ("RuleB",)

            def applies(self, context: DecisionContext) -> bool:
                return True

            def evaluate(self, context: DecisionContext) -> RuleResult:
                return self._result(passed=True, action=None, reason="A")

        return RuleA()

    def _cycle_rule_b(self) -> BaseRule:
        class RuleB(BaseRule):
            auto_register = False
            default_priority = 10
            runs_after = ("RuleA",)

            def applies(self, context: DecisionContext) -> bool:
                return True

            def evaluate(self, context: DecisionContext) -> RuleResult:
                return self._result(passed=True, action=None, reason="B")

        return RuleB()

    def _failing_rule(self) -> BaseRule:
        class FailingRule(BaseRule):
            auto_register = False
            default_priority = 30

            def applies(self, context: DecisionContext) -> bool:
                return True

            def evaluate(self, context: DecisionContext) -> RuleResult:
                return self._result(passed=False, action=None, reason="Failing rule failed.")

        return FailingRule()

    def _passing_rule(self, action: BaseAction) -> BaseRule:
        class PassingRule(BaseRule):
            auto_register = False
            default_priority = 20

            def applies(self, context: DecisionContext) -> bool:
                return True

            def evaluate(self, context: DecisionContext) -> RuleResult:
                return self._result(passed=True, action=action, reason="Passing rule passed.")

        return PassingRule()

    def _fallback_rule(self) -> BaseRule:
        class FallbackRule(BaseRule):
            auto_register = False
            default_priority = -1000
            is_fallback = True

            def applies(self, context: DecisionContext) -> bool:
                return True

            def evaluate(self, context: DecisionContext) -> RuleResult:
                action = context.legal_actions[0]
                return self._result(passed=True, action=action, reason="Fallback selected the first legal action.")

        return FallbackRule()

    def _make_temp_dir(self) -> Path:
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        path = TMP_ROOT / f"decision_{uuid.uuid4().hex}"
        path.mkdir(parents=True, exist_ok=True)
        return path


if __name__ == "__main__":
    unittest.main()
