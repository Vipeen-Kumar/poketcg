"""Main selection resolver that coordinates selection resolution."""

from poketcg.actions import BaseAction
from poketcg.domain import SelectPrompt

from .registry import SelectionResolverRegistry, get_default_registry


class SelectionResolver:
    """Coordinates resolution of selected actions into SDK indices.

    This is the public API for selection resolution. It uses a registry
    to dispatch to the appropriate specialized resolver based on the
    selection context.
    """

    def __init__(self, registry: SelectionResolverRegistry | None = None) -> None:
        """Initialize with an optional custom registry.

        Args:
            registry: The resolver registry to use. Defaults to the global registry.
        """
        self._registry = registry or get_default_registry()

    def resolve(self, action: BaseAction, selection: SelectPrompt) -> tuple[int, ...]:
        """Resolve a selected action into the indices to return to the SDK.

        Args:
            action: The action selected by the decision engine.
            selection: The current selection prompt from the environment.

        Returns:
            Tuple of indices to return to the environment.

        Raises:
            KeyError: If no resolver is registered for this selection context.
            ValueError: If the resolver produces invalid indices.
        """
        resolver = self._registry.get_resolver(selection.context)
        return resolver.resolve(action, selection)
