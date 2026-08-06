#!/usr/bin/env python
"""Quick test of combination action implementation."""

import sys
sys.path.insert(0, "src")

from poketcg.actions import ActionFactory
from poketcg.domain import (
    OptionReference,
    OptionType,
    SelectContext,
    SelectPrompt,
    SelectType,
    EffectContext,
)


def test_single_selection():
    """Test that single-selection still works."""
    factory = ActionFactory()
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
    actions = factory.from_selection(selection)
    assert len(actions) == 2, f"Expected 2 actions, got {len(actions)}"
    assert actions[0].selected_indices == (0,), f"Expected (0,), got {actions[0].selected_indices}"
    assert actions[1].selected_indices == (1,), f"Expected (1,), got {actions[1].selected_indices}"
    print("✓ Single-selection test passed")


def test_combination_generation():
    """Test that combinations are generated for minCount > 1."""
    factory = ActionFactory()
    selection = SelectPrompt(
        selection_type=SelectType.MAIN,
        context=SelectContext.TO_HAND,
        min_count=2,
        max_count=2,
        options=tuple(
            OptionReference(option_type=OptionType.CARD) for _ in range(3)
        ),
        effect_context=EffectContext(),
    )
    actions = factory.from_selection(selection)
    
    # Should generate C(3,2) = 3 combinations
    assert len(actions) == 3, f"Expected 3 actions, got {len(actions)}"
    
    # Check all combinations
    combinations = {action.selected_indices for action in actions}
    expected = {(0, 1), (0, 2), (1, 2)}
    assert combinations == expected, f"Expected {expected}, got {combinations}"
    
    # Check action_index returns first index
    for action in actions:
        first_idx = action.selected_indices[0]
        assert action.action_index == first_idx, \
            f"Expected action_index={first_idx}, got {action.action_index}"
    
    print("✓ Combination generation test passed")


def test_combination_mincount_3():
    """Test combinations with minCount=3."""
    factory = ActionFactory()
    selection = SelectPrompt(
        selection_type=SelectType.MAIN,
        context=SelectContext.TO_HAND,
        min_count=3,
        max_count=3,
        options=tuple(
            OptionReference(option_type=OptionType.CARD) for _ in range(4)
        ),
        effect_context=EffectContext(),
    )
    actions = factory.from_selection(selection)
    
    # Should generate C(4,3) = 4 combinations
    assert len(actions) == 4, f"Expected 4 actions, got {len(actions)}"
    
    combinations = {action.selected_indices for action in actions}
    expected = {(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)}
    assert combinations == expected, f"Expected {expected}, got {combinations}"
    
    print("✓ Combination minCount=3 test passed")


def test_optional_selection():
    """Test that minCount=0 still generates single actions."""
    factory = ActionFactory()
    selection = SelectPrompt(
        selection_type=SelectType.MAIN,
        context=SelectContext.TO_HAND,
        min_count=0,
        max_count=1,
        options=tuple(
            OptionReference(option_type=OptionType.CARD) for _ in range(3)
        ),
        effect_context=EffectContext(),
    )
    actions = factory.from_selection(selection)
    
    # Should still generate single-selection actions for minCount=0
    assert len(actions) == 3, f"Expected 3 actions, got {len(actions)}"
    for i, action in enumerate(actions):
        assert action.selected_indices == (i,), \
            f"Expected ({i},), got {action.selected_indices}"
    
    print("✓ Optional selection test passed")


if __name__ == "__main__":
    print("Testing combination action implementation...\n")
    test_single_selection()
    test_combination_generation()
    test_combination_mincount_3()
    test_optional_selection()
    print("\n✓ All tests passed! Implementation is correct.")
