"""Decision-engine context and configuration models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from poketcg.actions import BaseAction
from poketcg.analysis import GameAnalyzer
from poketcg.domain import GameState, Observation

from .exceptions import DecisionConfigurationError
from .results import DecisionTrace


@dataclass(slots=True, frozen=True)
class DecisionEngineConfig:
    """Runtime configuration for deterministic decision execution."""

    enabled_rules: tuple[str, ...] | None = None
    disabled_rules: tuple[str, ...] = ()
    priority_overrides: dict[str, int] = field(default_factory=dict)
    strict_mode: bool = True
    logging_enabled: bool = False
    plugin_modules: tuple[str, ...] = ()


@runtime_checkable
class DecisionTraceRecorder(Protocol):
    """Protocol for replay loggers or other decision-trace consumers."""

    def log_turn(
        self,
        observation: Observation,
        *,
        chosen_action: BaseAction | None = None,
        decision_metadata: object | None = None,
        decision_trace: DecisionTrace | None = None,
        analyzer: GameAnalyzer | None = None,
    ) -> object:
        """Record one decision-point snapshot."""


@dataclass(slots=True)
class DecisionContext:
    """Bundle the state required to make one deterministic decision."""

    analyzer: GameAnalyzer
    game_state: GameState | None = None
    legal_actions: tuple[BaseAction, ...] | None = None
    config: DecisionEngineConfig = field(default_factory=DecisionEngineConfig)
    replay_logger: DecisionTraceRecorder | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.game_state is None:
            self.game_state = self.analyzer.state
        elif self.analyzer.state is not None and self.game_state != self.analyzer.state:
            raise DecisionConfigurationError("DecisionContext game_state does not match analyzer.state.")

        if self.legal_actions is None:
            self.legal_actions = self.analyzer.actions()
        else:
            self.legal_actions = tuple(self.legal_actions)

    @property
    def observation(self) -> Observation:
        """Return the parsed observation behind this context."""

        return self.analyzer.observation
