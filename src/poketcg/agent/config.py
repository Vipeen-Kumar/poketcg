"""Baseline-agent configuration models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from poketcg.decision import DecisionEngineConfig
from poketcg.debug.replay_logger import ReplayLoggerConfig


@dataclass(slots=True, frozen=True)
class BaselineAgentConfig:
    """Configuration for the baseline submission agent."""

    deck_name: str = "baseline_deterministic"
    game_id_prefix: str = "game"
    safe_raw_fallback: bool = True
    decision: DecisionEngineConfig = field(
        default_factory=lambda: DecisionEngineConfig(logging_enabled=True),
    )
    replay: ReplayLoggerConfig = field(
        default_factory=lambda: ReplayLoggerConfig(
            enabled=True,
            output_directory=Path("outputs/replays"),
            markdown=True,
            json=True,
            maximum_saved_games=100,
        ),
    )
