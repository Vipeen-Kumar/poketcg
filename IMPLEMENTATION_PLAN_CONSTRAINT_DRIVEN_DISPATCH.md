# Implementation Plan: Constraint-Driven SelectionResolver Dispatch

**Date**: August 6, 2026  
**Status**: Planning (awaiting approval)

---

## PROBLEM STATEMENT

Current SelectionResolverRegistry dispatches resolvers based only on `SelectContext` enum:
```python
resolver = registry.get_resolver(context)  # Only uses context!
```

This fails because:
- Same context (e.g., SelectContext.TO_HAND) can appear with different minCount/maxCount
- GenericResolver only returns 1 index, fails when minCount > 1
- minCount/maxCount are ignored in dispatch decision

**Required**: Dispatch based on constraints, not context alone.

---

## SDK PROTOCOL VERIFICATION

From official environment.md:

```
SelectData fields:
  - minCount: lower bound on returned indices count
  - maxCount: upper bound on returned indices count

Agent returns:
  - list of option indices
  - len(result) must satisfy: minCount <= len(result) <= maxCount
```

**Example**:
- minCount=1, maxCount=1: agent returns [i] (exactly 1 index)
- minCount=2, maxCount=2: agent returns [i, j] (exactly 2 indices)
- minCount=0, maxCount=1: agent returns [] or [i] (0 or 1 index)

---

## SOLUTION ARCHITECTURE

### Core Principle

**Instead of**:
```
SelectContext enum → Resolver
```

**Use**:
```
SelectPrompt (with minCount/maxCount) → Resolver Strategy
  ├─ if minCount <= 1: GenericResolver (or constraint-aware version)
  └─ if minCount > 1: MultiSelectionResolver
```

### Implementation Strategy

1. **Rename/Enhance GenericResolver**
   - Current: Only handles minCount=1
   - Enhanced: Validate that minCount/maxCount are satisfied
   - Or: Keep unchanged and let MultiSelectionResolver handle > 1

2. **Create MultiSelectionResolver** (new)
   - Handles minCount > 1
   - Validates all constraints
   - Returns action.selected_indices directly (or subset if needed)

3. **Update SelectionResolverRegistry**
   - New method: `get_resolver_for_selection(selection: SelectPrompt) -> SelectionResolver`
   - Dispatches based on minCount, NOT context
   - Backward compatible: old `get_resolver(context)` still works for existing code

4. **Update BaselineAgent.act()**
   - Call new constraint-aware method
   - No other changes needed

---

## IMPLEMENTATION STEPS

### Step 1: Create MultiSelectionResolver

**File**: `src/poketcg/selection/multi.py` (new)

```python
class MultiSelectionResolver(SelectionResolver):
    """Handles multi-selection contexts where minCount > 1.
    
    Works for ANY context that requires returning multiple indices.
    Generic logic: just validate and return the selected indices.
    """
    
    def resolve(self, action: BaseAction, selection: SelectPrompt) -> tuple[int, ...]:
        """
        For multi-select, action.selected_indices should already be the chosen indices.
        
        Validate:
        - len(selected) >= minCount
        - len(selected) <= maxCount
        - all indices in range
        """
        indices = action.selected_indices
        
        if len(indices) < selection.min_count:
            raise ValueError(f"Need {selection.min_count} indices, got {len(indices)}")
        if len(indices) > selection.max_count:
            raise ValueError(f"Max {selection.max_count} indices, got {len(indices)}")
        
        for idx in indices:
            if idx < 0 or idx >= len(selection.options):
                raise ValueError(f"Index {idx} out of range [0, {len(selection.options)-1}]")
        
        return indices
```

### Step 2: Update SelectionResolverRegistry

**File**: `src/poketcg/selection/registry.py`

Add new method:
```python
def get_resolver_for_selection(self, selection: SelectPrompt) -> SelectionResolver:
    """Get resolver based on selection constraints, not just context.
    
    Dispatch logic:
    - If minCount > 1: use MultiSelectionResolver
    - Otherwise: use context-based lookup (backward compatible)
    """
    if selection.min_count > 1:
        return self._multi_resolver  # singleton
    else:
        return self.get_resolver(selection.context)  # original logic
```

Keep `_register_defaults()` unchanged.

### Step 3: Update BaselineAgent.act()

**File**: `src/poketcg/agent/baseline.py`

Change from:
```python
resolver = self._selection_resolver._registry.get_resolver(observation.selection.context)
resolved_indices = resolver.resolve(...)
```

To:
```python
resolver = self._selection_resolver._registry.get_resolver_for_selection(observation.selection)
resolved_indices = resolver.resolve(...)
```

### Step 4: Add Tests

**File**: `tests/selection/test_constraint_dispatch.py` (new)

```python
@pytest.mark.parametrize("min_count,max_count,expected_resolver_type", [
    (1, 1, GenericResolver),      # Single-select
    (0, 1, GenericResolver),      # Optional single
    (2, 2, MultiSelectionResolver),  # Required multi
    (2, 3, MultiSelectionResolver),  # Range multi
    (3, 5, MultiSelectionResolver),  # Larger multi
])
def test_resolver_dispatch_by_constraints(min_count, max_count, expected_resolver_type):
    """Verify resolver is chosen by constraints, not context."""
    # For same context, different constraints → different resolvers
```

Add regression tests:
```python
def test_to_hand_single_select():
    """TO_HAND with minCount=1 uses GenericResolver."""
    
def test_to_hand_multi_select():
    """TO_HAND with minCount=2 uses MultiSelectionResolver."""
    
def test_multi_selection_validation():
    """MultiSelectionResolver validates minCount/maxCount."""
    # Should raise ValueError if constraints violated
```

---

## BACKWARD COMPATIBILITY

1. **SelectionResolverRegistry.get_resolver(context)** remains unchanged
   - Old code still works
   - New code uses `get_resolver_for_selection(selection)`

2. **GenericResolver** unchanged
   - Still used for minCount ≤ 1
   - Single-select behavior preserved

3. **PrizeResolver** unchanged
   - May become deprecated later (MultiSelectionResolver handles it)
   - But still works if explicitly registered

4. **BaselineAgent integration**
   - Only change: call new method in act()
   - All other code unchanged

---

## EXPECTED OUTCOMES

### Test Coverage

- [x] Existing 99 tests still pass
- [x] New constraint-dispatch tests pass
- [x] minCount=1 contexts use GenericResolver
- [x] minCount=0,maxCount=1 contexts use GenericResolver
- [x] minCount≥2 contexts use MultiSelectionResolver
- [x] Validation errors raised for constraint violations

### Game Testing

- 100-game run completes without INVALID from multi-selection
- TO_HAND with minCount=2 now returns [0, 1] instead of [0]
- Same context (TO_HAND) works correctly with any minCount/maxCount

### Code Quality

- No breaking changes
- Minimal diff (≈50 lines of new code)
- Generic solution (no hardcoded context mappings)
- Clear separation: constraints drive dispatch, not context enum

---

## FILES TO BE MODIFIED/CREATED

| File | Type | Change |
|------|------|--------|
| `src/poketcg/selection/multi.py` | NEW | MultiSelectionResolver class |
| `src/poketcg/selection/registry.py` | MODIFY | Add get_resolver_for_selection() |
| `src/poketcg/selection/__init__.py` | MODIFY | Export MultiSelectionResolver |
| `src/poketcg/agent/baseline.py` | MODIFY | Use get_resolver_for_selection() |
| `tests/selection/test_constraint_dispatch.py` | NEW | Constraint-based dispatch tests |
| `tests/selection/test_multi_selection_resolver.py` | NEW | MultiSelectionResolver tests |

---

## VERIFICATION CHECKLIST

Before → After:
- [ ] 99 existing tests pass
- [ ] New tests pass
- [ ] Python syntax valid
- [ ] No circular imports
- [ ] BaselineAgent.act() works correctly
- [ ] SelectionResolver.resolve() called correctly
- [ ] Constraints validated
- [ ] INVALID errors eliminated
- [ ] 100-game run completes successfully

---

## MINIMAL DIFF PHILOSOPHY

- Only add what's necessary
- Don't redesign other components
- GenericResolver unchanged (backward compat)
- PrizeResolver can remain (may become deprecated)
- No changes to DecisionEngine, ActionFactory, Rules
- Constraint dispatch is self-contained in registry

