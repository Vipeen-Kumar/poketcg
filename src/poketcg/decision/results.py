"""Decision result and trace models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING

from poketcg.utils.serialization import to_serializable

if TYPE_CHECKING:
    from poketcg.actions import BaseAction


def summarize_action(action: BaseAction) -> dict[str, object]:
    """Return a serializable summary for a typed action."""

    return {
        "action_index": action.action_index,
        "kind": action.kind.name,
        "action_type": action.__class__.__name__,
        "selection_context": action.selection_context.name,
        "selection_type": action.selection_type.name,
        "metadata": to_serializable(action.metadata),
    }


@dataclass(slots=True, frozen=True)
class RuleResult:
    """Serializable outcome for one evaluated rule."""

    rule_name: str
    passed: bool
    selected_action: BaseAction | None
    reason: str
    priority: int
    metadata: dict[str, object] = field(default_factory=dict)
    execution_time: float = 0.0

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation."""

        payload = asdict(self)
        if self.selected_action is not None:
            payload["selected_action"] = summarize_action(self.selected_action)
        return to_serializable(payload)


@dataclass(slots=True, frozen=True)
class DecisionTrace:
    """Serializable execution trace for one decision."""

    rule_results: tuple[RuleResult, ...]
    selected_action: BaseAction | None = None
    selected_rule_name: str | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def selected_result(self) -> RuleResult | None:
        """Return the winning rule result, if any."""

        if not self.rule_results:
            return None
        return self.rule_results[-1]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-friendly representation."""

        payload = asdict(self)
        if self.selected_action is not None:
            payload["selected_action"] = summarize_action(self.selected_action)
        payload["rule_results"] = [result.to_dict() for result in self.rule_results]
        return to_serializable(payload)


@dataclass(slots=True, frozen=True)
class DecisionOutcome:
    """Typed action plus the trace used to select it."""

    action: BaseAction
    trace: DecisionTrace
