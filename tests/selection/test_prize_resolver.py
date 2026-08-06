"""Unit tests for PrizeResolver."""

import unittest

from poketcg.actions.enums import ActionKind
from poketcg.actions.models import CardChoiceAction
from poketcg.domain import (
    Card,
    EffectContext,
    OptionReference,
    OptionType,
    SelectContext,
    SelectPrompt,
    SelectType,
)
from poketcg.selection.prize import PrizeResolver


class PrizeResolverTestCase(unittest.TestCase):
    """Test PrizeResolver for multi-selection prize contexts."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.resolver = PrizeResolver()

    def test_resolve_satisfies_mincount_maxcount(self):
        """PrizeResolver accepts selections that satisfy minCount/maxCount."""
        action = CardChoiceAction(
            selected_indices=(0, 1),  # Select 2 prizes
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
        self.assertEqual(result, (0, 1))

    def test_resolve_violates_mincount_raises(self):
        """PrizeResolver raises if selection violates minCount."""
        action = CardChoiceAction(
            selected_indices=(0,),  # Only 1 prize selected
            kind=ActionKind.CHOOSE_CARD,
            option=OptionReference(option_type=OptionType.CARD),
            selection_context=SelectContext.TO_PRIZE,
            selection_type=SelectType.MAIN,
        )

        selection = SelectPrompt(
            selection_type=SelectType.MAIN,
            context=SelectContext.TO_PRIZE,
            min_count=2,  # Need at least 2
            max_count=2,
            options=(
                OptionReference(option_type=OptionType.CARD),
                OptionReference(option_type=OptionType.CARD),
            ),
            effect_context=EffectContext(),
        )

        with self.assertRaises(ValueError):
            self.resolver.resolve(action, selection)

    def test_resolve_violates_maxcount_raises(self):
        """PrizeResolver raises if selection violates maxCount."""
        action = CardChoiceAction(
            selected_indices=(0, 1, 2),  # 3 prizes selected
            kind=ActionKind.CHOOSE_CARD,
            option=OptionReference(option_type=OptionType.CARD),
            selection_context=SelectContext.TO_PRIZE,
            selection_type=SelectType.MAIN,
        )

        selection = SelectPrompt(
            selection_type=SelectType.MAIN,
            context=SelectContext.TO_PRIZE,
            min_count=2,
            max_count=2,  # Can only select 2
            options=(
                OptionReference(option_type=OptionType.CARD),
                OptionReference(option_type=OptionType.CARD),
                OptionReference(option_type=OptionType.CARD),
            ),
            effect_context=EffectContext(),
        )

        with self.assertRaises(ValueError):
            self.resolver.resolve(action, selection)

    def test_resolve_out_of_range_index_raises(self):
        """PrizeResolver raises if indices are out of range."""
        action = CardChoiceAction(
            selected_indices=(0, 5),  # Index 5 is out of range
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

        with self.assertRaises(ValueError):
            self.resolver.resolve(action, selection)

    def test_resolve_negative_index_raises(self):
        """PrizeResolver raises if indices are negative."""
        action = CardChoiceAction(
            selected_indices=(-1, 0),
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
