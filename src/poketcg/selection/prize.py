"""Resolver for prize card selection (multi-selection)."""

from poketcg.actions import BaseAction
from poketcg.domain import SelectContext, SelectPrompt

from .base import SelectionResolver


class PrizeResolver(SelectionResolver):
    """Resolves prize card selection with minCount/maxCount constraints.

    Prize selection is a multi-selection context where the player must choose
    exactly minCount to maxCount prize cards from available options.

    This resolver ensures the selection respects the environment's constraints.
    """

    def resolve(self, action: BaseAction, selection: SelectPrompt) -> tuple[int, ...]:
        """Convert action to indices for prize selection.

        For prize selection contexts, this resolver handles the multi-selection
        logic. Since prize selection is binary (player chooses which cards),
        the action's selected_indices directly represent the prize indices.

        Args:
            action: The action selected by the decision engine.
            selection: The prize selection prompt with minCount/maxCount.

        Returns:
            Tuple of indices representing selected prize cards.
            Satisfies: minCount <= len(result) <= maxCount

        Raises:
            ValueError: If the selection violates constraints.
        """
        import sys
        print(f"[FORENSIC-PRIZE] PrizeResolver.resolve() called", file=sys.stderr)
        print(f"[FORENSIC-PRIZE] selected_indices={action.selected_indices}", file=sys.stderr)
        print(f"[FORENSIC-PRIZE] minCount={selection.min_count}", file=sys.stderr)
        print(f"[FORENSIC-PRIZE] maxCount={selection.max_count}", file=sys.stderr)
        
        indices = action.selected_indices

        # Validate constraint satisfaction
        if len(indices) < selection.min_count:
            error_msg = f"Prize selection returned {len(indices)} indices but minCount={selection.min_count}"
            print(f"[FORENSIC-PRIZE] CONSTRAINT VIOLATION: {error_msg}", file=sys.stderr)
            raise ValueError(error_msg)
        if len(indices) > selection.max_count:
            error_msg = f"Prize selection returned {len(indices)} indices but maxCount={selection.max_count}"
            print(f"[FORENSIC-PRIZE] CONSTRAINT VIOLATION: {error_msg}", file=sys.stderr)
            raise ValueError(error_msg)

        # Validate indices are within range
        max_index = len(selection.options) - 1
        for idx in indices:
            if idx < 0 or idx > max_index:
                error_msg = f"Prize selection index {idx} out of range [0, {max_index}]"
                print(f"[FORENSIC-PRIZE] OUT OF RANGE: {error_msg}", file=sys.stderr)
                raise ValueError(error_msg)

        print(f"[FORENSIC-PRIZE] Validation passed, returning {indices}", file=sys.stderr)
        return indices
