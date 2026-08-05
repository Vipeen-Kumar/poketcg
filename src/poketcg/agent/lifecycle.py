"""Baseline-agent lifecycle helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypeAlias

from poketcg.domain import ActionSelection, Deck, Observation

RawObservation: TypeAlias = Mapping[str, object]
SubmissionResponse: TypeAlias = list[int]


class AgentLifecycle:
    """Utility methods for deck-selection and gameplay branching."""

    @staticmethod
    def is_deck_selection_payload(observation: Observation | RawObservation) -> bool:
        """Return whether the payload represents the initial deck-selection handshake."""

        if isinstance(observation, Observation):
            return observation.state is None and observation.selection is None
        
        # Check if observation is wrapped in "observation" key (Kaggle format)
        observation_data = observation
        if "observation" in observation and isinstance(observation["observation"], Mapping):
            observation_data = observation["observation"]
        
        current = observation_data.get("current")
        select = observation_data.get("select")
        return current is None and select is None

    @staticmethod
    def serialize_deck(deck: Deck) -> SubmissionResponse:
        """Convert a deck object into the Kaggle-facing list payload."""

        return list(deck.card_ids)

    @staticmethod
    def serialize_action_selection(selection: ActionSelection) -> SubmissionResponse:
        """Convert an action selection into the Kaggle-facing list payload."""

        return list(selection.selected_option_indices)

    @staticmethod
    def emergency_first_legal_action(observation: RawObservation) -> SubmissionResponse | None:
        """Return a last-resort raw legal selection when typed parsing fails."""

        # Check if observation is wrapped in "observation" key (Kaggle format)
        observation_data = observation
        if "observation" in observation and isinstance(observation["observation"], Mapping):
            observation_data = observation["observation"]
        
        select = observation_data.get("select")
        if not isinstance(select, Mapping):
            return None
        options = select.get("option")
        if not isinstance(options, Sequence) or isinstance(options, (str, bytes)) or len(options) == 0:
            return None
        return [0]
