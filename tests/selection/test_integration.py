"""Integration tests for SelectionResolver with BaselineAgent."""

import unittest

from poketcg.actions.enums import ActionKind
from poketcg.actions.models import CardChoiceAction, EndTurnAction
from poketcg.domain import (
    EffectContext,
    OptionReference,
    OptionType,
    SelectContext,
    SelectPrompt,
    SelectType,
)
from poketcg.selection.resolver import SelectionResolver


class SelectionResolverIntegrationTestCase(unittest.TestCase):
    """Test SelectionResolver integration with the action/decision flow."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.resolver = SelectionResolver()

    def test_resolve_single_select_main_context(self):
        """Resolver correctly handles single-select MAIN context."""
        action = EndTurnAction(
            selected_indices=(0,),
            kind=ActionKind.END_TURN,
            option=OptionReference(option_type=OptionType.END),
            selection_context=SelectContext.MAIN,
            selection_type=SelectType.MAIN,
        )

        selection = SelectPrompt(
            selection_type=SelectType.MAIN,
            context=SelectContext.MAIN,
            min_count=1,
            max_count=1,
            options=(OptionReference(option_type=OptionType.END),),
            effect_context=EffectContext(),
        )

        result = self.resolver.resolve(action, selection)
        self.assertEqual(result, (0,))

    def test_resolve_multi_select_prize_context(self):
        """Resolver correctly handles multi-select TO_PRIZE context."""
        action = CardChoiceAction(
            selected_indices=(1, 2),
            kind=ActionKind.CHOOSE_CARD,
            option=OptionReference(option_type=OptionType.CARD),
            selection_context=SelectContext.TO_PRIZE,
            selection_type=SelectType.MAIN,
        )

        selection = SelectPrompt(
            selection_type=SelectType.MAIN,
            context=SelectContext.TO_PRIZE,
            min_count=2,
            max_count=2,
            options=(
                OptionReference(option_type=OptionType.CARD),
                OptionReference(option_type=OptionType.CARD),
                OptionReference(option_type=OptionType.CARD),
            ),
            effect_context=EffectContext(),
        )

        result = self.resolver.resolve(action, selection)
        self.assertEqual(result, (1, 2))

    def test_resolve_raises_on_invalid_prize_selection(self):
        """Resolver raises on invalid prize selection constraints."""
        action = CardChoiceAction(
            selected_indices=(0,),  # Only 1, need 2
            kind=ActionKind.CHOOSE_CARD,
            option=OptionReference(option_type=OptionType.CARD),
            selection_context=SelectContext.TO_PRIZE,
            selection_type=SelectType.MAIN,
        )

        selection = SelectPrompt(
            selection_type=SelectType.MAIN,
            context=SelectContext.TO_PRIZE,
            min_count=2,
            max_count=2,
            options=(
                OptionReference(option_type=OptionType.CARD),
                OptionReference(option_type=OptionType.CARD),
            ),
            effect_context=EffectContext(),
        )

        with self.assertRaises(ValueError):
            self.resolver.resolve(action, selection)


if __name__ == "__main__":
    unittest.main()
