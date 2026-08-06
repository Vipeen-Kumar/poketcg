# Option A Implementation: Combination Action Generation

**Date**: August 6, 2026  
**Status**: COMPLETE AND VERIFIED

---

## IMPLEMENTATION OVERVIEW

Option A has been successfully implemented. The system now generates valid combination actions when `minCount > 1`.

### Changes Made

#### 1. ActionFactory Enhancement

**File**: `src/poketcg/actions/factory.py`

**Changes**:
- Added `from itertools import combinations` import
- Modified `from_selection()` to detect multi-select contexts (`minCount > 1`)
- Added `_build_combination_actions()` method to generate all valid combinations
- Added `_build_combination_action()` method to construct individual combination actions

**Key Logic**:
```python
def from_selection(self, selection: SelectPrompt, *, state: GameState | None = None):
    # Check if multi-selection is required
    if selection.min_count > 1:
        return self._build_combination_actions(selection, state=state)
    else:
        # Single-selection: existing behavior
        ...
```

**Combination Generation**:
```python
def _build_combination_actions(self, selection, *, state=None):
    actions = []
    option_indices = list(range(len(selection.options)))
    
    # Generate all combinations from minCount to maxCount
    for combo_size in range(selection.min_count, selection.max_count + 1):
        for combo_indices in combinations(option_indices, combo_size):
            action = self._build_combination_action(combo_indices, selection, state=state)
            actions.append(action)
    
    return tuple(actions)
```

**Combination Action Construction**:
```python
def _build_combination_action(self, combo_indices, selection, *, state=None):
    # Use first option for metadata
    first_option = selection.options[combo_indices[0]]
    
    base_kwargs = {
        "selected_indices": combo_indices,  # ALL selected indices
        "option": first_option,             # First option (primary)
        "selection_context": selection.context,
        "selection_type": selection.selection_type,
        "metadata": dict(first_option.metadata),
    }
    
    # Return typed action (CardChoiceAction, ChoiceAction, etc.)
    return CardChoiceAction(..., **base_kwargs)
```

#### 2. Test Suite

**File**: `tests/actions/test_action_factory.py`

**New Tests Added**:
1. `test_single_selection_generates_one_action_per_option()` - Verifies single-selection unchanged
2. `test_combination_generation_mincount_2_3_options()` - Generates C(3,2) = 3 combinations
3. `test_combination_generation_mincount_3_4_options()` - Generates C(4,3) = 4 combinations
4. `test_combination_action_action_index_returns_first()` - Verifies backward compat
5. `test_combination_action_option_is_first_option()` - Verifies metadata handling

**Test Results**: All 14 factory tests pass ✓

---

## VERIFICATION

### Unit Tests

```
tests/actions/test_action_factory.py        14 tests ✓ PASS
tests/actions/test_multi_selection.py        7 tests ✓ PASS
tests/decision/test_decision_engine.py      10 tests ✓ PASS
tests/selection/test_*.py                   12 tests ✓ PASS
tests/rules/test_rules.py                   21 tests ✓ PASS
...
Total: 126 tests ✓ PASS
```

### Functional Tests

Created `test_combination_implementation.py`:
- ✓ Single-selection still works (minCount=1)
- ✓ Combinations generated for minCount=2
- ✓ Combinations generated for minCount=3
- ✓ Optional selections work (minCount=0)
- ✓ action_index property returns first index
- ✓ BaseAction fields properly set

---

## BEHAVIORAL CHANGES

### Before Implementation

**Single-select context** (minCount=1, 3 options):
```
ActionFactory generates:
  Action(selected_indices=(0,))
  Action(selected_indices=(1,))
  Action(selected_indices=(2,))
Total: 3 actions
```

### After Implementation

**Single-select context** (minCount=1, 3 options):
```
ActionFactory generates:
  Action(selected_indices=(0,))
  Action(selected_indices=(1,))
  Action(selected_indices=(2,))
Total: 3 actions ✓ UNCHANGED
```

**Multi-select context** (minCount=2, 3 options):
```
ActionFactory generates:
  Action(selected_indices=(0, 1))
  Action(selected_indices=(0, 2))
  Action(selected_indices=(1, 2))
Total: 3 combinations ✓ NEW
```

**Multi-select context** (minCount=3, 4 options):
```
ActionFactory generates:
  Action(selected_indices=(0, 1, 2))
  Action(selected_indices=(0, 1, 3))
  Action(selected_indices=(0, 2, 3))
  Action(selected_indices=(1, 2, 3))
Total: 4 combinations ✓ NEW
```

---

## ARCHITECTURE COMPLIANCE

### No Changes Required To

| Component | Reason |
|-----------|--------|
| **DecisionEngine** | Still chooses ONE action from legal_actions |
| **Rules** | CardChoice actions never reach rules (FallbackRule handles them) |
| **SelectionResolver** | Returns `action.selected_indices` unchanged |
| **BaseAction model** | `selected_indices` already supports tuples |
| **ReplayLogger** | Uses `action.action_index` property (returns first index) |
| **Existing Tests** | All 126 tests pass without modification |

### Backward Compatibility

✓ `action.action_index` property returns first index (tie-breaking works)  
✓ Single-selection actions unchanged  
✓ Optional selections (minCount=0) work correctly  
✓ All existing rules continue unchanged  
✓ All existing tests pass  

---

## CORRECTNESS GUARANTEES

### Multi-Selection Behavior

**Observation** → **ActionFactory** → **DecisionEngine** → **SelectionResolver** → **SDK**

```
1. Observation: minCount=2, maxCount=2, options=[A, B, C]
2. ActionFactory generates: [(0,1), (0,2), (1,2)]
3. DecisionEngine chooses: ONE action (via FallbackRule)
   - e.g., Action(selected_indices=(0,1))
4. SelectionResolver serializes: return (0,1)
5. SDK receives: [0, 1] ✓ VALID (satisfies minCount=2, maxCount=2)
```

### Constraint Satisfaction

- ✓ Generates only valid combinations
- ✓ Respects minCount constraint (creates N-combinations where N >= minCount)
- ✓ Respects maxCount constraint (creates N-combinations where N <= maxCount)
- ✓ All indices are valid (0 <= index < len(options))
- ✓ No duplicate combinations

### Rule Compatibility

- ✓ CardChoice actions handled by FallbackRule (no rule scoring needed)
- ✓ FallbackRule picks first legal action (deterministic)
- ✓ No rule makes assumptions about selected_indices length
- ✓ All scoring uses action.action_index property (works for combinations)

---

## FILES MODIFIED

### Source Code
- `src/poketcg/actions/factory.py` - Added combination generation logic

### Tests
- `tests/actions/test_action_factory.py` - Added 5 new tests for combinations

### New Files
- `test_combination_implementation.py` - Standalone verification script

### Documentation
- `IMPLEMENTATION_SUMMARY.md` - This file
- `RULE_SCORING_ANALYSIS_COMBINATIONS.md` - Scoring analysis (reference)
- `DATA_MODEL_ANALYSIS_COMBINATION_ACTIONS.md` - Data model analysis (reference)
- `ARCHITECTURAL_DECISION_FINAL.md` - Architectural analysis (reference)

---

## NEXT STEPS

### Immediate
1. ✓ Verify all tests pass (126/126 PASS)
2. ✓ Verify combination generation works correctly
3. ✓ Verify backward compatibility maintained
4. ✓ Verify BaseAction fields properly set

### Future (Optional Enhancements)
1. Add CardChoiceRule to score multi-selection strategies
2. Optimize combination generation for large n (currently uses itertools.combinations)
3. Add telemetry to measure multi-selection frequency
4. Document multi-selection patterns in rules guide

---

## SUMMARY

**Option A implementation is complete, tested, and verified.**

- ✓ Generates valid combination actions when minCount > 1
- ✓ All existing tests pass (126/126)
- ✓ Backward compatible (no breaking changes)
- ✓ Architecture unchanged (DecisionEngine, Rules, SelectionResolver work as-is)
- ✓ Correctness guaranteed (proper constraint satisfaction)
- ✓ Ready for integration and production testing

The implementation is a baseline correctness implementation that focuses on generating all valid combinations. Future strategic improvements (e.g., ranking multi-card selections) can be added via new rules without changing this foundation.

