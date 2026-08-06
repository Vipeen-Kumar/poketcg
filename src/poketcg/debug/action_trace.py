"""Detailed action pipeline tracing for debugging illegal actions."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Any

from poketcg.actions import BaseAction
from poketcg.domain import Observation, SelectPrompt


@dataclass(slots=True)
class ActionTraceEntry:
    """Single trace entry for an action decision."""

    turn: int
    step: int
    player_index: int
    select_type: str
    select_context: str
    legal_option_count: int
    raw_select_option: list[dict[str, Any]]
    parsed_actions: list[dict[str, Any]]
    chosen_action: dict[str, Any] | None
    returned_integer: int | None
    validation_passed: bool
    validation_error: str | None
    decision_error: str | None


class ActionTraceCollector:
    """Collect and manage action traces for debugging."""

    def __init__(self) -> None:
        self._traces: list[ActionTraceEntry] = []
        self._turn_counter = 0
        self._step_counter = 0

    def trace_decision(
        self,
        observation: Observation,
        legal_actions: tuple[BaseAction, ...],
        chosen_action: BaseAction | None,
        returned_integer: int | None,
        validation_passed: bool = True,
        validation_error: str | None = None,
        decision_error: str | None = None,
    ) -> None:
        """Record a single decision trace."""

        if observation.selection is None:
            return

        selection = observation.selection
        state = observation.state

        # Determine turn and player
        turn = state.turn if state is not None else 0
        player_idx = state.current_player.value if state is not None and state.current_player is not None else 0

        entry = ActionTraceEntry(
            turn=turn,
            step=self._step_counter,
            player_index=player_idx,
            select_type=selection.selection_type.name if selection.selection_type is not None else "UNKNOWN",
            select_context=selection.context.name if selection.context is not None else "UNKNOWN",
            legal_option_count=len(selection.options) if selection.options is not None else 0,
            raw_select_option=self._serialize_options(selection.options),
            parsed_actions=self._serialize_actions(legal_actions),
            chosen_action=self._serialize_action(chosen_action),
            returned_integer=returned_integer,
            validation_passed=validation_passed,
            validation_error=validation_error,
            decision_error=decision_error,
        )

        self._traces.append(entry)
        self._step_counter += 1

    def log_turn_summary(self) -> str:
        """Get formatted summary of all traces."""

        output = []
        output.append("\n" + "=" * 100)
        output.append("ACTION PIPELINE TRACE")
        output.append("=" * 100)

        for i, trace in enumerate(self._traces):
            output.append(f"\n--- Decision {i + 1} ---")
            output.append(f"Turn: {trace.turn} | Step: {trace.step} | Player: {trace.player_index}")
            output.append(f"Select Type: {trace.select_type} | Context: {trace.select_context}")
            output.append(f"Legal Options: {trace.legal_option_count}")

            output.append(f"\nRaw select.option:")
            for j, opt in enumerate(trace.raw_select_option):
                output.append(f"  [{j}] {opt}")

            output.append(f"\nParsed Actions ({len(trace.parsed_actions)}):")
            for action in trace.parsed_actions:
                output.append(f"  Index {action['index']}: {action['type']} - {action['description']}")

            if trace.chosen_action:
                output.append(f"\nChosen Action:")
                output.append(f"  Index: {trace.chosen_action['index']}")
                output.append(f"  Type: {trace.chosen_action['type']}")
                output.append(f"  Description: {trace.chosen_action['description']}")

            output.append(f"\nReturned to Environment: {trace.returned_integer}")

            if trace.decision_error:
                output.append(f"Decision Error: {trace.decision_error}")

            if not trace.validation_passed:
                output.append(f"VALIDATION FAILED: {trace.validation_error}")
            else:
                output.append("Validation: PASSED")

            # Check if returned integer matches legal options
            if trace.returned_integer is not None and trace.legal_option_count > 0:
                if trace.returned_integer >= trace.legal_option_count or trace.returned_integer < 0:
                    output.append(f"\n!!! ILLEGAL ACTION DETECTED !!!")
                    output.append(f"Returned index {trace.returned_integer} out of bounds [0, {trace.legal_option_count - 1}]")

        output.append("\n" + "=" * 100)
        return "\n".join(output)

    def get_traces(self) -> list[ActionTraceEntry]:
        """Get all traces."""
        return list(self._traces)

    def to_json(self) -> str:
        """Export traces as JSON."""
        return json.dumps([asdict(trace) for trace in self._traces], indent=2, default=str)

    @staticmethod
    def _serialize_options(options: tuple | list | None) -> list[dict[str, Any]]:
        """Serialize option references."""
        if not options:
            return []
        result = []
        for opt in options:
            opt_dict = {
                "type": opt.option_type.name if opt.option_type is not None else "UNKNOWN",
            }
            if hasattr(opt, "metadata") and opt.metadata:
                opt_dict["metadata"] = dict(opt.metadata)
            result.append(opt_dict)
        return result

    @staticmethod
    def _serialize_actions(actions: tuple[BaseAction, ...] | None) -> list[dict[str, Any]]:
        """Serialize actions."""
        if not actions:
            return []
        result = []
        for action in actions:
            result.append(
                {
                    "index": action.action_index,
                    "type": action.__class__.__name__,
                    "description": ActionTraceCollector._describe_action(action),
                }
            )
        return result

    @staticmethod
    def _serialize_action(action: BaseAction | None) -> dict[str, Any] | None:
        """Serialize a single action."""
        if action is None:
            return None
        return {
            "index": action.action_index,
            "type": action.__class__.__name__,
            "description": ActionTraceCollector._describe_action(action),
        }

    @staticmethod
    def _describe_action(action: BaseAction) -> str:
        """Create human-readable action description."""
        from poketcg.actions import (
            AttackAction,
            AttachEnergyAction,
            EndTurnAction,
            EvolutionAction,
            PlayCardAction,
            RetreatAction,
        )

        if isinstance(action, AttackAction):
            return f"Attack: {action.attack_name}" if action.attack_name else "Attack (unknown)"
        elif isinstance(action, RetreatAction):
            return f"Retreat to {action.target_pokemon.name}" if action.target_pokemon else "Retreat"
        elif isinstance(action, PlayCardAction):
            return f"Play: {action.card.name}" if action.card else "Play card"
        elif isinstance(action, AttachEnergyAction):
            return f"Attach {action.card.name if action.card else 'energy'}"
        elif isinstance(action, EvolutionAction):
            return f"Evolve: {action.evolution_card.name if action.evolution_card else 'unknown'}"
        elif isinstance(action, EndTurnAction):
            return "End Turn"
        else:
            return f"{action.__class__.__name__}"


# Global trace collector
_global_trace_collector: ActionTraceCollector | None = None


def get_trace_collector() -> ActionTraceCollector:
    """Get or create the global trace collector."""
    global _global_trace_collector
    if _global_trace_collector is None:
        _global_trace_collector = ActionTraceCollector()
    return _global_trace_collector


def reset_trace_collector() -> None:
    """Reset the global trace collector."""
    global _global_trace_collector
    _global_trace_collector = ActionTraceCollector()
