"""Factory helpers for baseline-agent construction."""

from __future__ import annotations

import poketcg.rules  # noqa: F401  # Ensure rule auto-registration side effects.

from poketcg.actions import ActionFactory
from poketcg.cards import CardDatabase
from poketcg.debug import ReplayLogger
from poketcg.decision import DecisionEngine
from poketcg.engine import ObservationParser

from .baseline import BaselineAgent
from .config import BaselineAgentConfig


def create_baseline_agent(config: BaselineAgentConfig | None = None) -> BaselineAgent:
    """Build the default baseline agent and its dependencies."""

    resolved_config = config or BaselineAgentConfig()
    card_database = CardDatabase()
    card_database.load()
    parser = ObservationParser(card_database)
    action_factory = ActionFactory()
    decision_engine = DecisionEngine()
    replay_logger = ReplayLogger(resolved_config.replay, action_factory=action_factory)
    return BaselineAgent(
        config=resolved_config,
        card_database=card_database,
        observation_parser=parser,
        action_factory=action_factory,
        decision_engine=decision_engine,
        replay_logger=replay_logger,
    )
