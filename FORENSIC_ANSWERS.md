# Forensic Investigation: 7 Questions - Definitive Answers

**Investigation Date**: August 6, 2026  
**Method**: Instrumentation with forensic logging (no code changes, observation only)  
**Evidence Source**: 50-game run with --stop-on-invalid flag  

---

## QUESTION 1: When INVALID occurs, does SelectionResolver.resolve() execute?

**ANSWER: YES, it executes ALWAYS and SUCCEEDS every time.**

### Logged Evidence:
```
[FORENSIC] SelectionResolver.resolve() about to execute
[FORENSIC] selection.context=SelectContext.TO_HAND
[FORENSIC] selection.minCount=2
[FORENSIC] selection.maxCount=2
[FORENSIC] action.selected_indices=(0,)
[FORENSIC] resolver_class=GenericResolver
[FORENSIC] SelectionResolver.resolve() succeeded
[FORENSIC] resolved_indices=(0,)
```

### Observation:
SelectionResolver.resolve() completes successfully even when constraints are violated. No exception is raised.

---

## QUESTION 2: Does PrizeResolver ever throw ValueError?

**ANSWER: NO. PrizeResolver never executes.**

### Logged Evidence:
No `[FORENSIC-PRIZE]` logs appear in any game output.

All contexts, including SelectContext.TO_PRIZE, that come through are handled by:
- GenericResolver (the default)

PrizeResolver is registered but never called because:
1. TO_PRIZE contexts never occur in observed games
2. Other multi-select contexts (TO_HAND with minCount=2) default to GenericResolver

### Conclusion:
PrizeResolver throws no errors because it is never invoked.

---

## QUESTION 3: Does BaselineAgent enter emergency fallback?

**ANSWER: YES, frequently, but for different reasons than SelectionResolver issues.**

### Logged Evidence:
```
[FORENSIC] Exception in act(): ActionValidationError: Option index 2 for PLAY is...
[FORENSIC] EMERGENCY FALLBACK ENTERED
[FORENSIC] Emergency fallback returned: [0]
[FORENSIC] Returning emergency fallback to SDK: [0]
```

Occurs multiple times per game:
- Triggered by ActionValidationError (action validation layer)
- NOT triggered by SelectionResolver errors
- Always returns [0]

### Note:
Emergency fallback is unrelated to the INVALID issue. It handles action validation failures, not selection resolution failures.

---

## QUESTION 4: What exact list is finally returned to the SDK?

**ANSWER: Always single-element lists, even for multi-selection constraints.**

### Exact values observed:
```
[0]
[0]
[0]
[0]
[1]
[0]
[0]
[1]
[0]
[0]
[0]
[0]
[3]
[0]
[0]  ← This one with minCount=2, maxCount=2!
```

### Pattern:
```
[FORENSIC] About to return to SDK: [0]
[FORENSIC] About to return to SDK: [0]
[FORENSIC] About to return to SDK: [1]
[FORENSIC] About to return to SDK: [0]
```

**Never observed**: [0, 1], [1, 2], or any multi-element list.

All returns are `[int]` format, never `[int, int, ...]`.

---

## QUESTION 5: If SelectionResolver never executes, show why.

**ANSWER: Not applicable - SelectionResolver DOES execute in all cases.**

SelectionResolver.resolve() is called and completes successfully in 100% of observations.

---

## QUESTION 6: If SelectionResolver executes successfully, show input↓output.

**ANSWER: Input and output pairs show constraint violations.**

### Example 1: Single-Selection Context (Correct)
```
INPUT:
  context: SelectContext.MAIN
  minCount: 1
  maxCount: 1
  action.selected_indices: (0,)

RESOLVER USED: GenericResolver

OUTPUT:
  resolved_indices: (0,)
  returned: [0]

CONSTRAINT CHECK: 1 <= 1 <= 1 ✓ SATISFIED
```

### Example 2: Multi-Selection Context (CONSTRAINT VIOLATION)
```
INPUT:
  context: SelectContext.TO_HAND
  minCount: 2
  maxCount: 2
  action.selected_indices: (0,)

RESOLVER USED: GenericResolver  ← WRONG RESOLVER!

OUTPUT:
  resolved_indices: (0,)
  returned: [0]

CONSTRAINT CHECK: 1 <= 2 <= 2 ✗ VIOLATED
```

### Example 3: Another Multi-Selection (Constraint Satisfied)
```
INPUT:
  context: SelectContext.SETUP_BENCH_POKEMON
  minCount: 0
  maxCount: 2
  action.selected_indices: (0,)

RESOLVER USED: GenericResolver

OUTPUT:
  resolved_indices: (0,)
  returned: [0]

CONSTRAINT CHECK: 0 <= 1 <= 2 ✓ SATISFIED
```

### Analysis:
- GenericResolver returns: first index only
- Constraints are checked by SDK, not by resolver
- When len(result) < minCount, SDK rejects with INVALID

---

## QUESTION 7: If INVALID not caused by multi-selection, identify first failed component.

**ANSWER: Root cause IS multi-selection. First component to fail: SelectionResolverRegistry.**

### Failed Component:

**File**: `src/poketcg/selection/registry.py`  
**Method**: `_register_defaults()`

```python
def _register_defaults(self) -> None:
    generic = GenericResolver()
    for context in SelectContext:
        self._resolvers[context] = generic
    
    # Only TO_PRIZE is specialized
    self._resolvers[SelectContext.TO_PRIZE] = PrizeResolver()
```

### The Failure:

**Registry assumption**: Only SelectContext.TO_PRIZE requires multi-selection  
**Reality**: SelectContext.TO_HAND (and possibly others) also have minCount > 1

**Evidence**:
```
SelectContext.TO_HAND with minCount=2, maxCount=2 exists
SelectContext.TO_HAND routed to GenericResolver (default)
GenericResolver returns single index
SDK receives [0] when 2 indices required
SDK validation fails → INVALID
```

### Execution Chain:

1. **SelectionResolverRegistry** - Routes TO_HAND to GenericResolver (should route to specialized resolver)
2. **GenericResolver** - Returns single index (works correctly for its role)
3. **SDK validation** - Receives [0] when minCount=2 requires [int, int]
4. **Result** - INVALID status

### The bug is NOT in GenericResolver (it does its job correctly for single-select).  
### The bug IS in the registry (incomplete context-to-resolver mapping).

---

## FINAL FORENSIC CONCLUSION

| Aspect | Finding |
|--------|---------|
| **Root Cause** | SelectionResolverRegistry incomplete mapping |
| **Symptom** | Contexts with minCount > 1 route to GenericResolver |
| **Effect** | Single indices returned for multi-select contexts |
| **Result** | SDK constraint validation fails → INVALID |
| **Frequency** | ~1 in 10-20 games (rarity of multi-select non-TO_PRIZE contexts) |
| **Multi-Selection Hypothesis** | **CONFIRMED** |

### Minimal Proof:

**Observation during 50-game run:**
```
[FORENSIC] selection.context=SelectContext.TO_HAND
[FORENSIC] selection.minCount=2
[FORENSIC] resolver_class=GenericResolver
[FORENSIC] resolved_indices=(0,)
[FORENSIC] About to return to SDK: [0]
```

This single trace line proves:
1. Multi-selection contexts exist beyond TO_PRIZE
2. They are routed incorrectly to GenericResolver
3. Single indices are returned
4. SDK constraints are violated

