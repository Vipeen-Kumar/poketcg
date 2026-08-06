"""Unit tests for multi-selection action support."""

import unittest

from poketcg.actions.enums import ActionKind
from poketcg.actions.models import BaseAction, EndTurnAction, PlayCardAction
from poketcg.domain import (
    OptionReference,
    OptionType,
    SelectContext,
    SelectType,
)


class MultiSelectionActionTestCase(unittest.TestCase):
    """Test multi-selection action support."""

    def test_single_selection_action_has_one_index(self):
        """Single-selection actions contain exactly one index."""
        action = EndTurnAction(
            selected_indices=(0,),
            kind=ActionKind.END_TURN,
            option=OptionReference(option_type=OptionType.END),
            selection_context=SelectContext.MAIN,
            selection_type=SelectType.MAIN,
        )
        self.assertEqual(len(action.selected_indices), 1)
        self.assertEqual(action.selected_indices[0], 0)

    def test_backward_compat_action_index_property_single_select(self):
        """Backward compatibility: action_index property returns first index."""
        action = EndTurnAction(
            selected_indices=(5,),
            kind=ActionKind.END_TURN,
            option=OptionReference(option_type=OptionType.END),
            selection_context=SelectContext.MAIN,
            selection_type=SelectType.MAIN,
        )
        # Should return the first (and only) index
        self.assertEqual(action.action_index, 5)

    def test_multi_selection_action_has_multiple_indices(self):
        """Multi-selection actions can contain multiple indices."""
        action = EndTurnAction(
            selected_indices=(0, 1, 2),
            kind=ActionKind.END_TURN,
            option=OptionReference(option_type=OptionType.END),
            selection_context=SelectContext.MAIN,
            selection_type=SelectType.MAIN,
        )
        self.assertEqual(len(action.selected_indices), 3)
        self.assertEqual(action.selected_indices, (0, 1, 2))

    def test_backward_compat_action_index_property_multi_select(self):
        """Backward compatibility: action_index returns first index for multi-select."""
        action = EndTurnAction(
            selected_indices=(2, 5, 7),
            kind=ActionKind.END_TURN,
            option=OptionReference(option_type=OptionType.END),
            selection_context=SelectContext.MAIN,
            selection_type=SelectType.MAIN,
        )
        # Should return the first index even for multi-select
        self.assertEqual(action.action_index, 2)

    def test_empty_selection_indices(self):
        """Actions can have empty selection indices."""
        action = EndTurnAction(
            selected_indices=(),
            kind=ActionKind.END_TURN,
            option=OptionReference(option_type=OptionType.END),
            selection_context=SelectContext.MAIN,
            selection_type=SelectType.MAIN,
        )
        self.assertEqual(len(action.selected_indices), 0)

    def test_backward_compat_action_index_property_empty(self):
        """Backward compatibility: action_index returns -1 for empty selection."""
        action = EndTurnAction(
            selected_indices=(),
            kind=ActionKind.END_TURN,
            option=OptionReference(option_type=OptionType.END),
            selection_context=SelectContext.MAIN,
            selection_type=SelectType.MAIN,
        )
        # Should return -1 when no indices selected
        self.assertEqual(action.action_index, -1)

    def test_selected_indices_is_immutable_tuple(self):
        """Selected indices are stored as immutable tuples."""
        action = EndTurnAction(
            selected_indices=(0, 1),
            kind=ActionKind.END_TURN,
            option=OptionReference(option_type=OptionType.END),
            selection_context=SelectContext.MAIN,
            selection_type=SelectType.MAIN,
        )
        # Verify it's a tuple, not a list
        self.assertIsInstance(action.selected_indices, tuple)
        # Verify immutability by attempting to modify
        with self.assertRaises((TypeError, AttributeError)):
            action.selected_indices[0] = 999


if __name__ == "__main__":
    unittest.main()
