"""Unit tests for GenericResolver."""

import unittest

from poketcg.actions.enums import ActionKind
from poketcg.actions.models import EndTurnAction
from poketcg.domain import (
    OptionReference,
    OptionType,
    SelectContext,
    SelectType,
)
from poketcg.selection.generic import GenericResolver


class GenericResolverTestCase(unittest.TestCase):
    """Test GenericResolver for single-selection contexts."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.resolver = GenericResolver()

    def test_resolve_single_index_returns_tuple(self):
        """GenericResolver returns a single-element tuple for single indices."""
        action = EndTurnAction(
            selected_indices=(0,),
            kind=ActionKind.END_TURN,
            option=OptionReference(option_type=OptionType.END),
            selection_context=SelectContext.MAIN,
            selection_type=SelectType.MAIN,
        )
        from poketcg.domain import EffectContext, SelectPrompt

        selection = SelectPrompt(
            selection_type=SelectType.MAIN,
            context=SelectContext.MAIN,
            min_count=1,
            max_count=1,
            options=(
                OptionReference(option_type=OptionType.END),
                OptionReference(option_type=OptionType.END),
            ),
            effect_context=EffectContext(),
        )

        result = self.resolver.resolve(action, selection)
        self.assertEqual(result, (0,))

    def test_resolve_multiple_indices_returns_all(self):
        """GenericResolver returns all indices when multiple are present."""
        action = EndTurnAction(
            selected_indices=(2, 5, 7),  # Multiple indices
            kind=ActionKind.END_TURN,
            option=OptionReference(option_type=OptionType.END),
            selection_context=SelectContext.MAIN,
            selection_type=SelectType.MAIN,
        )
        from poketcg.domain import EffectContext, SelectPrompt

        selection = SelectPrompt(
            selection_type=SelectType.MAIN,
            context=SelectContext.MAIN,
            min_count=1,
            max_count=1,
            options=(OptionReference(option_type=OptionType.END),) * 10,
            effect_context=EffectContext(),
        )

        result = self.resolver.resolve(action, selection)
        # Should return all indices as provided
        self.assertEqual(result, (2, 5, 7))

    def test_resolve_empty_indices_returns_empty(self):
        """GenericResolver returns empty tuple for empty indices."""
        action = EndTurnAction(
            selected_indices=(),
            kind=ActionKind.END_TURN,
            option=OptionReference(option_type=OptionType.END),
            selection_context=SelectContext.MAIN,
            selection_type=SelectType.MAIN,
        )
        from poketcg.domain import EffectContext, SelectPrompt

        selection = SelectPrompt(
            selection_type=SelectType.MAIN,
            context=SelectContext.MAIN,
            min_count=1,
            max_count=1,
            options=(OptionReference(option_type=OptionType.END),),
            effect_context=EffectContext(),
        )

        result = self.resolver.resolve(action, selection)
        self.assertEqual(result, ())


if __name__ == "__main__":
    unittest.main()
