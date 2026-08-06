"""Base class for selection resolvers."""

from abc import ABC, abstractmethod

from poketcg.actions import BaseAction
from poketcg.domain import SelectPrompt


class SelectionResolver(ABC):
    """Base class for resolving selected actions into SDK indices."""

    @abstractmethod
    def resolve(self, action: BaseAction, selection: SelectPrompt) -> tuple[int, ...]:
        """Convert a selected action into the indices to return to the SDK.

        Args:
            action: The action selected by the decision engine.
            selection: The current selection prompt from the environment.

        Returns:
            Tuple of indices to return to the environment.
            Must satisfy: len(result) >= selection.min_count and len(result) <= selection.max_count
        """
        pass
