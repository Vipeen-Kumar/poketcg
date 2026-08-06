"""Deterministic decision engine."""

from __future__ import annotations

from importlib import import_module

from poketcg.actions import BaseAction

from .context import DecisionContext
from .exceptions import DecisionConfigurationError, EmptyLegalActionError, MissingFallbackRuleError, UnknownRuleError
from .registry import RuleRegistry, get_default_registry
from .results import DecisionOutcome, DecisionTrace, RuleResult


class BaseRule:
    """Reusable abstract rule interface."""

    rule_name: str | None = None
    default_priority: int = 0
    runs_before: tuple[str, ...] = ()
    runs_after: tuple[str, ...] = ()
    is_fallback: bool = False
    auto_register: bool = True

    def __init__(self) -> None:
        self._enabled = True
        self._priority_override: int | None = None

    @property
    def name(self) -> str:
        """Return the rule name used for registration and tracing."""

        return self.rule_name or self.__class__.__name__

    @property
    def priority(self) -> int:
        """Return the current rule priority."""

        if self._priority_override is not None:
            return self._priority_override
        return self.default_priority

    @property
    def enabled(self) -> bool:
        """Return whether the rule is enabled."""

        return self._enabled

    def enable(self) -> None:
        """Enable the rule."""

        self._enabled = True

    def disable(self) -> None:
        """Disable the rule."""

        self._enabled = False

    def set_priority(self, priority: int) -> None:
        """Override the rule priority for this instance."""

        self._priority_override = priority

    def clear_priority_override(self) -> None:
        """Remove any priority override for this instance."""

        self._priority_override = None

    def applies(self, context: DecisionContext) -> bool:
        """Return whether the rule can apply to the current context."""

        return True

    def evaluate(self, context: DecisionContext) -> RuleResult:
        """Evaluate the rule and return a serializable result."""

        raise NotImplementedError

    def _result(
        self,
        *,
        passed: bool,
        action: BaseAction | None,
        reason: str,
        metadata: dict[str, object] | None = None,
        execution_time: float = 0.0,
    ) -> RuleResult:
        return RuleResult(
            rule_name=self.name,
            passed=passed,
            selected_action=action,
            reason=reason,
            priority=self.priority,
            metadata={} if metadata is None else dict(metadata),
            execution_time=execution_time,
        )

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        # Skip registration for abstract base classes
        if cls is BaseRule or not getattr(cls, "auto_register", True):
            return
        # Skip if rule_name is not set (indicates an intermediate base class)
        if getattr(cls, "rule_name", None) is None and cls.__name__ == "BaseRule":
            return
        get_default_registry().register(cls())


class DecisionEngine:
    """Deterministic rule executor that always returns one legal action."""

    def __init__(self, registry: RuleRegistry | None = None) -> None:
        self._registry = registry if registry is not None else get_default_registry()
        self._last_outcome: DecisionOutcome | None = None

    @property
    def last_outcome(self) -> DecisionOutcome | None:
        """Return the most recent decision outcome."""

        return self._last_outcome

    def choose_action(self, context: DecisionContext) -> BaseAction:
        """Choose a single action for the current decision context."""

        outcome = self.decide(context)
        return outcome.action

    def decide(self, context: DecisionContext) -> DecisionOutcome:
        """Return the selected action together with the execution trace."""

        if context.config.plugin_modules:
            if self._registry is not get_default_registry():
                raise DecisionConfigurationError("Plugin loading currently targets the shared registry only.")
            for module_name in context.config.plugin_modules:
                import_module(module_name)

        working_registry = self._registry.copy()
        self._apply_configuration(working_registry, context)

        if not context.legal_actions:
            raise EmptyLegalActionError("DecisionEngine requires at least one legal action.")

        evaluated_results: list[RuleResult] = []
        for rule in working_registry.ordered_rules():
            if not rule.applies(context):
                result = self._failed_result(rule, context, "Rule does not apply to the current context.")
            else:
                result = rule.evaluate(context)
            evaluated_results.append(result)
            if result.passed:
                # Validate that the selected action is in the legal actions
                if result.selected_action is None:
                    raise InvalidRuleError(f"Rule {rule.name} passed but selected_action is None.")
                if result.selected_action not in context.legal_actions:
                    raise InvalidRuleError(
                        f"Rule {rule.name} returned action not in legal_actions. "
                        f"Action index: {getattr(result.selected_action, 'action_index', 'N/A')}, "
                        f"Legal actions count: {len(context.legal_actions)}"
                    )
                import sys
                action = result.selected_action
                print(f"[TRACE-ENGINE] Rule {rule.name} selected action", file=sys.stderr)
                print(f"[TRACE-ENGINE] selected_indices={action.selected_indices} id={id(action)}", file=sys.stderr)
                return self._finalize_outcome(
                    context=context,
                    evaluated_results=evaluated_results,
                    selected_result=result,
                    fallback_used=False,
                    fallback_reason=None,
                )

        fallback_rule = working_registry.fallback_rule()
        fallback_result = fallback_rule.evaluate(context)
        evaluated_results.append(fallback_result)
        
        # Validate fallback rule result too
        if fallback_result.passed:
            if fallback_result.selected_action is None:
                raise InvalidRuleError("Fallback rule passed but selected_action is None.")
            if fallback_result.selected_action not in context.legal_actions:
                raise InvalidRuleError(
                    f"Fallback rule returned action not in legal_actions. "
                    f"Action index: {getattr(fallback_result.selected_action, 'action_index', 'N/A')}, "
                    f"Legal actions count: {len(context.legal_actions)}"
                )
        
        if not fallback_result.passed:
            raise MissingFallbackRuleError("The fallback rule failed to select an action.")

        return self._finalize_outcome(
            context=context,
            evaluated_results=evaluated_results,
            selected_result=fallback_result,
            fallback_used=True,
            fallback_reason=fallback_result.reason,
        )

    def _apply_configuration(self, registry: RuleRegistry, context: DecisionContext) -> None:
        enabled_rules = context.config.enabled_rules
        disabled_rules = set(context.config.disabled_rules)
        priority_overrides = context.config.priority_overrides

        if enabled_rules is not None:
            known_rules = {rule.name for rule in registry.all_rules()}
            missing = [rule_name for rule_name in enabled_rules if rule_name not in known_rules]
            if missing and context.config.strict_mode:
                raise UnknownRuleError(f"Unknown enabled rules: {', '.join(missing)}.")
            enabled_set = set(enabled_rules)
            for rule in registry.all_rules():
                if not rule.is_fallback and rule.name not in enabled_set:
                    rule.disable()

        if disabled_rules:
            known_rules = {rule.name for rule in registry.all_rules()}
            missing = sorted(disabled_rules - known_rules)
            if missing and context.config.strict_mode:
                raise UnknownRuleError(f"Unknown disabled rules: {', '.join(missing)}.")
            for rule in registry.all_rules():
                if rule.name in disabled_rules:
                    rule.disable()

        for rule_name, priority in priority_overrides.items():
            try:
                registry.get(rule_name).set_priority(priority)
            except UnknownRuleError:
                if context.config.strict_mode:
                    raise

    def _failed_result(self, rule: BaseRule, context: DecisionContext, reason: str) -> RuleResult:
        return RuleResult(
            rule_name=rule.name,
            passed=False,
            selected_action=None,
            reason=reason,
            priority=rule.priority,
            metadata={"legal_action_count": len(context.legal_actions)},
            execution_time=0.0,
        )

    def _finalize_outcome(
        self,
        *,
        context: DecisionContext,
        evaluated_results: list[RuleResult],
        selected_result: RuleResult,
        fallback_used: bool,
        fallback_reason: str | None,
    ) -> DecisionOutcome:
        trace = DecisionTrace(
            rule_results=tuple(evaluated_results),
            selected_action=selected_result.selected_action,
            selected_rule_name=selected_result.rule_name,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            metadata=dict(context.metadata),
        )
        outcome = DecisionOutcome(action=selected_result.selected_action, trace=trace)
        self._last_outcome = outcome
        self._log_trace(context, outcome)
        return outcome

    def _log_trace(self, context: DecisionContext, outcome: DecisionOutcome) -> None:
        logger = context.replay_logger
        if logger is None or not context.config.logging_enabled:
            return

        log_turn = getattr(logger, "log_turn", None)
        if not callable(log_turn):
            return

        log_turn(
            context.observation,
            chosen_action=outcome.action,
            decision_trace=outcome.trace,
            analyzer=context.analyzer,
        )
