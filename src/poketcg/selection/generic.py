"""Generic resolver for single-selection contexts."""

from poketcg.actions import BaseAction
from poketcg.domain import SelectPrompt

from .base import SelectionResolver


class GenericResolver(SelectionResolver):
    """Resolves single-selection prompts where one action = one index.

    This handles all standard single-selection contexts where the action's
    first (and only) selected index directly maps to the selection.
    """

    def resolve(self, action: BaseAction, selection: SelectPrompt) -> tuple[int, ...]:
        """Convert action to index tuple for single-selection.

        For single-selection contexts (minCount=1, maxCount=1),
        return the first selected index as a single-element tuple.

        Args:
            action: The action selected by the decision engine.
            selection: The current selection prompt.

        Returns:
            Tuple containing the single selected index.
        """
        import sys
        print(f"[TRACE-GENERIC] GenericResolver.resolve() called", file=sys.stderr)
        print(f"[TRACE-GENERIC] action id={id(action)}", file=sys.stderr)
        print(f"[TRACE-GENERIC] action.selected_indices={action.selected_indices}", file=sys.stderr)
        print(f"[TRACE-GENERIC] selection.min_count={selection.min_count}", file=sys.stderr)
        print(f"[TRACE-GENERIC] selection.max_count={selection.max_count}", file=sys.stderr)
        
        if not action.selected_indices:
            print(f"[TRACE-GENERIC] Returning empty tuple", file=sys.stderr)
            return ()

        # Return the full tuple - supports both single-select and multi-select
        result = action.selected_indices
        print(f"[TRACE-GENERIC] Returning result={result}", file=sys.stderr)
        return result
