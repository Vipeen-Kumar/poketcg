# Root Cause: GenericResolver Returns Only First Index

**Date**: August 6, 2026  
**Analysis**: Complete Forensic Trace of First INVALID Action  
**Games Analyzed**: 5/5 all resulted in INVALID status

---

## EXECUTIVE SUMMARY

The first INVALID action occurs when:
1. SDK requests **exactly 2 cards** (minCount=2, maxCount=2)
2. ActionFactory generates combination action with **selected_indices=(0, 1)**
3. DecisionEngine selects that action (correct)
4. **GenericResolver.resolve() returns (0,) instead of (0, 1)**
5. SDK receives [0] but expects [0, 1]
6. SDK rejects: list length 1 does not match requirement of 2
7. Game status: INVALID

---

## THE EVIDENCE

### From Game 5 Debug Output

**Step 82: Multi-select TO_HAND selection**

```
[FORENSIC] SelectionResolver.resolve() about to execute
[FORENSIC] selection.context=SelectContext.TO_HAND
[FORENSIC] selection.minCount=2
[FORENSIC] selection.maxCount=2
[FORENSIC] action.selected_indices=(0, 1)
[FORENSIC] resolver_class=GenericResolver
[FORENSIC-GENERIC] GenericResolver.resolve() called
[FORENSIC-GENERIC] selected_indices=(0, 1)
[FORENSIC-GENERIC] minCount=2
[FORENSIC-GENERIC] maxCount=2
[FORENSIC-GENERIC] Returning (0,)
[FORENSIC] SelectionResolver.resolve() succeeded
[FORENSIC] resolved_indices=(0,)
[FORENSIC] About to return to SDK: [0]
[FORENSIC] act() succeeded, returning to SDK: [0]
```

### Pattern Across All Games

This pattern repeats in every game in the 5-game run:

```
> [FORENSIC] action.selected_indices=(0, 1)
  [FORENSIC] resolver_class=GenericResolver
> [FORENSIC-GENERIC] minCount=2
  [FORENSIC-GENERIC] maxCount=2
  [FORENSIC-GENERIC] Returning (0,)
```

**Occurrence count**: Multiple times per game whenever minCount/maxCount=2

---

## THE SOURCE CODE

**File**: `src/poketcg/selection/generic.py`  
**Lines**: 34-38

```python
# For single-selection, return the first (primary) index
result = (action.selected_indices[0],)
print(f"[FORENSIC-GENERIC] Returning {result}", file=sys.stderr)
return result
```

**The Bug**: 
```python
result = (action.selected_indices[0],)
```

This explicitly extracts ONLY the first element from the tuple, discarding all others.

### When action.selected_indices=(0, 1)

```python
action.selected_indices[0]  # Returns: 0
result = (0,)              # Creates single-element tuple
return result              # Returns: (0,)
```

The second index (1) is completely discarded.

---

## WHAT SHOULD HAPPEN

### For Single-Select (minCount=1, maxCount=1)
- **Input**: action.selected_indices=(0,)
- **Current output**: (0,) ✓ CORRECT
- **Always returns first element**: Works by coincidence

### For Multi-Select (minCount=2, maxCount=2)
- **Input**: action.selected_indices=(0, 1)
- **Expected output**: (0, 1)
- **Actual output**: (0,) ✗ WRONG
- **Always returns first element only**: DISCARDS second element

---

## PRECISE FAILURE POINT

**Location**: `GenericResolver.resolve()` line 38  
**Input received**: `action.selected_indices=(0, 1)` with `min_count=2, max_count=2`  
**Output produced**: `(0,)`  
**Output expected**: `(0, 1)`

**Consequence**:
- Returned to SDK: `[0]` (length 1)
- SDK expects: `[0, 1]` (length 2)
- SDK validation fails: "Selection length 1 does not match minCount=2"
- Result: INVALID game status

---

## VALIDATION CHECKLIST

### 1. Does the combination action reach GenericResolver?
**✓ YES** - Trace shows: `resolver_class=GenericResolver`

### 2. Is GenericResolver receiving the full tuple?
**✓ YES** - Trace shows: `selected_indices=(0, 1)`

### 3. Does GenericResolver return only first element?
**✓ YES** - Trace shows: `Returning (0,)`

### 4. Does SDK reject the shortened tuple?
**✓ YES** - Games 1-5 all end with INVALID status

### 5. Is this the FIRST point of deviation?
**✓ YES** - Everything before this point is correct:
- Observation parsed correctly
- Combination action generated correctly
- DecisionEngine selected combination correctly
- Only GenericResolver corrupts the data

---

## THE PROBLEM STATEMENT

GenericResolver is designed for single-selection contexts (minCount=1, maxCount=1).

When it encounters a multi-select action (minCount≥2), it:
1. **Receives**: Full tuple like (0, 1)
2. **Extracts**: Only [0]
3. **Returns**: Incomplete tuple
4. **Result**: SDK validation fails

The resolver doesn't validate that `len(selected_indices) == 1` before returning only the first index.

---

## CONCLUSION

**The FIRST point where our output differs from SDK expectations:**

GenericResolver.resolve() receives a combination action with selected_indices=(0, 1) when minCount=2, maxCount=2, but returns only (0,) instead of preserving the full tuple (0, 1).

This causes the SDK to receive [0] (length 1) when it requires [0, 1] (length 2), triggering the INVALID status.
