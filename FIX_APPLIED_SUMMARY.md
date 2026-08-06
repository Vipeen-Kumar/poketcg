# Fix Applied: GenericResolver Multi-Select Support

**Date**: August 6, 2026  
**Status**: ✅ COMPLETE AND VERIFIED

---

## The Fix

**File**: `src/poketcg/selection/generic.py`  
**Method**: `GenericResolver.resolve()`  
**Line**: 31

### Changed From:
```python
result = (action.selected_indices[0],)
```

### Changed To:
```python
result = action.selected_indices
```

### Why This Works:

The original code extracted only the first element from the tuple:
- Input: `(0, 1)` → Extract: `[0]` → Output: `(0,)`
- This discarded all indices after the first one

The fixed code returns the full tuple as-is:
- Input: `(0, 1)` → Return: `(0, 1)` ✓
- Input: `(0,)` → Return: `(0,)` ✓
- Input: `()` → Return: `()` ✓

This simple change respects the action's selected_indices regardless of whether it contains one index or multiple indices.

---

## Test Update

**File**: `tests/selection/test_generic_resolver.py`

Updated test `test_resolve_multiple_indices_returns_first_only` to `test_resolve_multiple_indices_returns_all`:
- Old expectation: `(2,)` when given `(2, 5, 7)`
- New expectation: `(2, 5, 7)` when given `(2, 5, 7)`

This reflects the correct behavior where all indices are preserved.

---

## Verification Results

### Unit Tests
✅ **126/126 tests pass**
- All action factory tests pass
- All decision engine tests pass
- All selection resolver tests pass
- All rule tests pass

### Integration Tests - Game Execution

**5 games**: All DONE (0 INVALID) ✅  
**20 games**: All DONE (0 INVALID) ✅  
**50 games**: All DONE (0 INVALID) ✅

### Before Fix
- Games 1-5: Multiple INVALID statuses
- Issue: Multi-select actions returned incomplete index lists

### After Fix
- Games 1-50: All DONE, no INVALID statuses
- Multi-select actions correctly return all selected indices
- Single-select actions continue to work as before

---

## What the Fix Does

### For Single-Select Actions (minCount=1, maxCount=1):
- **Before**: Returns `(0,)` ✓
- **After**: Returns `(0,)` ✓
- **Result**: Unchanged, backward compatible

### For Multi-Select Actions (minCount=2, maxCount=N):
- **Before**: Returns `(0,)` when given `(0, 1)` ✗
- **After**: Returns `(0, 1)` when given `(0, 1)` ✓
- **Result**: Fixed, now supports multi-selection

### For Empty Actions:
- **Before**: Returns `()` ✓
- **After**: Returns `()` ✓
- **Result**: Unchanged

---

## Architecture Implications

✅ **No redesign needed**
✅ **No new components required**
✅ **ActionFactory continues working as designed**
✅ **DecisionEngine continues working as designed**
✅ **BaselineAgent continues working as designed**
✅ **Only GenericResolver behavior corrected**

The fix is **minimal, surgical, and elegant**:
- One line changed
- One test updated
- Everything else works unchanged

---

## Root Cause Fixed

**The Problem**: GenericResolver was designed for single-selection contexts but was receiving multi-select actions.

**The Symptom**: Multi-select actions returned incomplete index lists, causing SDK validation to fail.

**The Root Cause**: Explicit extraction of only the first index: `result = (action.selected_indices[0],)`

**The Solution**: Return the complete tuple: `result = action.selected_indices`

---

## Deployment Ready

✅ All tests pass  
✅ All games execute without INVALID status  
✅ Backward compatibility maintained  
✅ No configuration changes needed  
✅ No new dependencies  
✅ No breaking changes  

**Status**: Ready for Kaggle submission
