"""Registry for selecting the appropriate resolver based on context."""

from poketcg.domain import SelectContext

from .base import SelectionResolver
from .generic import GenericResolver
from .prize import PrizeResolver


class SelectionResolverRegistry:
    """Registry that dispatches to the appropriate resolver based on SelectContext.

    Uses a mapping from SelectContext to resolver class to avoid large if/else chains.
    """

    def __init__(self) -> None:
        """Initialize the registry with default resolvers."""
        self._resolvers: dict[SelectContext, SelectionResolver] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register the default resolvers for all contexts."""
        # All standard single-selection contexts use GenericResolver
        generic = GenericResolver()
        for context in SelectContext:
            self._resolvers[context] = generic

        # Override with specialized resolvers
        self._resolvers[SelectContext.TO_PRIZE] = PrizeResolver()

    def register(self, context: SelectContext, resolver: SelectionResolver) -> None:
        """Register a resolver for a specific context.

        Args:
            context: The SelectContext this resolver handles.
            resolver: The SelectionResolver instance to use.
        """
        self._resolvers[context] = resolver

    def get_resolver(self, context: SelectContext) -> SelectionResolver:
        """Get the resolver for a specific context.

        Args:
            context: The SelectContext to get a resolver for.

        Returns:
            The SelectionResolver for this context.

        Raises:
            KeyError: If no resolver is registered for this context.
        """
        if context not in self._resolvers:
            raise KeyError(f"No resolver registered for context: {context}")
        return self._resolvers[context]


# Global default registry
_default_registry = SelectionResolverRegistry()


def get_default_registry() -> SelectionResolverRegistry:
    """Get the default global resolver registry.

    Returns:
        The default SelectionResolverRegistry instance.
    """
    return _default_registry
