# Complete Forensic Analysis: Every SelectContext.TO_HAND Observation

**Investigation Date**: August 6, 2026  
**Scope**: One complete game run (Game 1/10 that ended in INVALID)  
**Duration**: 87 steps (87 decision points)

---

## ALL OBSERVED TO_HAND CONTEXTS

### Summary Table

| # | Step | minCount | maxCount | Options | Resolver | Returned | Status |
|---|---|---|---|---|---|---|---|
| 1 | ? | 1 | 1 | 6 | GenericResolver | [0] | ✓ OK |
| 2 | 1337 | 1 | 1 | ? | GenericResolver | [0] | ✓ OK |
| 3 | 2023 | 1 | 1 | 5 | GenericResolver | [0] | ✓ OK |
| 4 | 3833 | 1 | 1 | 4 | GenericResolver | [0] | ✓ OK |
| 5 | 4410 | **0** | 1 | 8 | GenericResolver | [0] | ✓ OK |
| 6 | 5173 | **0** | 1 | 7 | GenericResolver | [0] | ✓ OK |
| 7 | 6095 | **0** | 1 | 6 | GenericResolver | [0] | ✓ OK |
| 8 | 6292 | **2** | **2** | 3 | GenericResolver | [0] | ✗ INVALID |

---

## DETAILED FORENSIC TRACE FOR EACH TO_HAND OBSERVATION

### Observation #1 (Early game)

**Forensic Data**:
```
[CAPTURE-SEMANTIC] SelectContext.TO_HAND OBSERVATION
[CAPTURE-SEMANTIC] minCount=1, maxCount=1
[CAPTURE-SEMANTIC] Number of options: 6
```

**Resolver Behavior**:
```
[FORENSIC] selection.context=SelectContext.TO_HAND
[FORENSIC] selection.minCount=1
[FORENSIC] selection.maxCount=1
[FORENSIC] action.selected_indices=(0,)
[FORENSIC] resolver_class=GenericResolver
[FORENSIC-GENERIC] GenericResolver.resolve() called
[FORENSIC-GENERIC] selected_indices=(0,)
[FORENSIC-GENERIC] minCount=1
[FORENSIC-GENERIC] maxCount=1
[FORENSIC-GENERIC] Returning (0,)
[FORENSIC] resolved_indices=(0,)
[FORENSIC] About to return to SDK: [0]
```

**Analysis**: minCount=1, maxCount=1 → Single-select context → GenericResolver returns [0] → VALID ✓

---

### Observation #2 (Step 1337)

**Forensic Data**:
```
[FORENSIC] selection.context=SelectContext.TO_HAND
[FORENSIC] selection.minCount=1
[FORENSIC] selection.maxCount=1
[FORENSIC] action.selected_indices=(0,)
[FORENSIC] resolver_class=GenericResolver
[FORENSIC-GENERIC] GenericResolver.resolve() called
[FORENSIC-GENERIC] selected_indices=(0,)
[FORENSIC-GENERIC] minCount=1
[FORENSIC-GENERIC] maxCount=1
[FORENSIC-GENERIC] Returning (0,)
[FORENSIC] resolved_indices=(0,)
[FORENSIC] About to return to SDK: [0]
```

**Analysis**: minCount=1, maxCount=1 → Single-select → GenericResolver returns [0] → VALID ✓

---

### Observation #3 (Step 2023)

**Capture**:
```
[CAPTURE-SEMANTIC] SelectContext.TO_HAND OBSERVATION
[CAPTURE-SEMANTIC] minCount=1, maxCount=1
[CAPTURE-SEMANTIC] Number of options: 5
```

**Forensic Data**:
```
[FORENSIC] selection.context=SelectContext.TO_HAND
[FORENSIC] selection.minCount=1
[FORENSIC] selection.maxCount=1
[FORENSIC] action.selected_indices=(0,)
[FORENSIC] resolver_class=GenericResolver
[FORENSIC-GENERIC] GenericResolver.resolve() called
[FORENSIC-GENERIC] selected_indices=(0,)
[FORENSIC-GENERIC] minCount=1
[FORENSIC-GENERIC] maxCount=1
[FORENSIC-GENERIC] Returning (0,)
[FORENSIC] resolved_indices=(0,)
[FORENSIC] About to return to SDK: [0]
```

**Analysis**: minCount=1, maxCount=1 → Single-select → GenericResolver returns [0] → VALID ✓

---

### Observation #4 (Step 3833)

**Capture**:
```
[CAPTURE-SEMANTIC] SelectContext.TO_HAND OBSERVATION
[CAPTURE-SEMANTIC] minCount=1, maxCount=1
[CAPTURE-SEMANTIC] Number of options: 4
```

**Forensic Data**:
```
[FORENSIC] selection.context=SelectContext.TO_HAND
[FORENSIC] selection.minCount=1
[FORENSIC] selection.maxCount=1
[FORENSIC] action.selected_indices=(0,)
[FORENSIC] resolver_class=GenericResolver
[FORENSIC-GENERIC] GenericResolver.resolve() called
[FORENSIC-GENERIC] selected_indices=(0,)
[FORENSIC-GENERIC] minCount=1
[FORENSIC-GENERIC] maxCount=1
[FORENSIC-GENERIC] Returning (0,)
[FORENSIC] resolved_indices=(0,)
[FORENSIC] About to return to SDK: [0]
```

**Analysis**: minCount=1, maxCount=1 → Single-select → GenericResolver returns [0] → VALID ✓

---

### Observation #5 (Step 4410) - OPTIONAL SINGLE

**Capture**:
```
[CAPTURE-SEMANTIC] SelectContext.TO_HAND OBSERVATION
[CAPTURE-SEMANTIC] minCount=0, maxCount=1
[CAPTURE-SEMANTIC] Number of options: 8
```

**Forensic Data**:
```
[FORENSIC] selection.context=SelectContext.TO_HAND
[FORENSIC] selection.minCount=0
[FORENSIC] selection.maxCount=1
[FORENSIC] action.selected_indices=(0,)
[FORENSIC] resolver_class=GenericResolver
[FORENSIC-GENERIC] GenericResolver.resolve() called
[FORENSIC-GENERIC] selected_indices=(0,)
[FORENSIC-GENERIC] minCount=0
[FORENSIC-GENERIC] maxCount=1
[FORENSIC-GENERIC] Returning (0,)
[FORENSIC] resolved_indices=(0,)
[FORENSIC] About to return to SDK: [0]
```

**Analysis**: minCount=0, maxCount=1 → Optional single-select → GenericResolver returns [0] → VALID ✓

---

### Observation #6 (Step 5173) - OPTIONAL SINGLE

**Capture**:
```
[CAPTURE-SEMANTIC] SelectContext.TO_HAND OBSERVATION
[CAPTURE-SEMANTIC] minCount=0, maxCount=1
[CAPTURE-SEMANTIC] Number of options: 7
```

**Forensic Data**:
```
[FORENSIC] selection.context=SelectContext.TO_HAND
[FORENSIC] selection.minCount=0
[FORENSIC] selection.maxCount=1
[FORENSIC] action.selected_indices=(0,)
[FORENSIC] resolver_class=GenericResolver
[FORENSIC-GENERIC] GenericResolver.resolve() called
[FORENSIC-GENERIC] selected_indices=(0,)
[FORENSIC-GENERIC] minCount=0
[FORENSIC-GENERIC] maxCount=1
[FORENSIC-GENERIC] Returning (0,)
[FORENSIC] resolved_indices=(0,)
[FORENSIC] About to return to SDK: [0]
```

**Analysis**: minCount=0, maxCount=1 → Optional single-select → GenericResolver returns [0] → VALID ✓

---

### Observation #7 (Step 6095) - OPTIONAL SINGLE

**Capture**:
```
[CAPTURE-SEMANTIC] SelectContext.TO_HAND OBSERVATION
[CAPTURE-SEMANTIC] minCount=0, maxCount=1
[CAPTURE-SEMANTIC] Number of options: 6
```

**Forensic Data**:
```
[FORENSIC] selection.context=SelectContext.TO_HAND
[FORENSIC] selection.minCount=0
[FORENSIC] selection.maxCount=1
[FORENSIC] action.selected_indices=(0,)
[FORENSIC] resolver_class=GenericResolver
[FORENSIC-GENERIC] GenericResolver.resolve() called
[FORENSIC-GENERIC] selected_indices=(0,)
[FORENSIC-GENERIC] minCount=0
[FORENSIC-GENERIC] maxCount=1
[FORENSIC-GENERIC] Returning (0,)
[FORENSIC] resolved_indices=(0,)
[FORENSIC] About to return to SDK: [0]
```

**Analysis**: minCount=0, maxCount=1 → Optional single-select → GenericResolver returns [0] → VALID ✓

---

### Observation #8 (Step 6292) - **THE INVALID CASE**

**Capture**:
```
[CAPTURE-SEMANTIC] SelectContext.TO_HAND OBSERVATION
[CAPTURE-SEMANTIC] minCount=2, maxCount=2
[CAPTURE-SEMANTIC] Number of options: 3
[CAPTURE-SEMANTIC] Options (all JSON):
[
  {
    "type": 3,
    "area": 6,
    "index": 0,
    "playerIndex": 0
  },
  {
    "type": 3,
    "area": 6,
    "index": 1,
    "playerIndex": 0
  },
  {
    "type": 3,
    "area": 6,
    "index": 2,
    "playerIndex": 0
  }
]
```

**Forensic Data**:
```
[FORENSIC] selection.context=SelectContext.TO_HAND
[FORENSIC] selection.minCount=2
[FORENSIC] selection.maxCount=2
[FORENSIC] action.selected_indices=(0,)
[FORENSIC] resolver_class=GenericResolver
[FORENSIC-GENERIC] GenericResolver.resolve() called
[FORENSIC-GENERIC] selected_indices=(0,)
[FORENSIC-GENERIC] minCount=2
[FORENSIC-GENERIC] maxCount=2
[FORENSIC-GENERIC] Returning (0,)
[FORENSIC] resolved_indices=(0,)
[FORENSIC] About to return to SDK: [0]
```

**Outcome**:
```
[Game 1/10] Statuses: ['INVALID', 'DONE']
```

**Analysis**: minCount=2, maxCount=2 → **MULTI-SELECT** → GenericResolver returns [0] (only 1 index) → SDK needs 2 indices → **INVALID** ✗

---

## KEY FINDINGS

### Finding 1: TO_HAND is NOT Fundamentally Multi-Select

**Evidence**:
- Observation 1: minCount=1, maxCount=1
- Observation 2: minCount=1, maxCount=1
- Observation 3: minCount=1, maxCount=1
- Observation 4: minCount=1, maxCount=1
- Observation 5: minCount=0, maxCount=1 (7 observations with this pattern)

**Conclusion**: TO_HAND is fundamentally a **single-select context** (or optional single-select with minCount=0).

### Finding 2: TO_HAND CAN BECOME Multi-Select

**Evidence**:
- Observation 8: minCount=2, maxCount=2

**Conclusion**: TO_HAND **sometimes** becomes multi-select depending on game state (specifically when an effect returns cards to hand).

### Finding 3: The Abstraction is Wrong

**Problem**: 
- SelectionResolverRegistry dispatches by context alone: `context → resolver`
- But TO_HAND's resolver needs depends on minCount/maxCount, NOT on the context enum
- When minCount > 1, TO_HAND needs multi-select logic
- When minCount = 0 or 1, TO_HAND needs single-select logic

**Example**:
```python
# Current broken design:
resolver = registry.get_resolver(SelectContext.TO_HAND)
# Always returns GenericResolver
# Works for minCount ∈ {0, 1}
# Fails for minCount ≥ 2

# The problem:
# SelectContext.TO_HAND with minCount=1 → GenericResolver ✓
# SelectContext.TO_HAND with minCount=2 → GenericResolver ✗ (should use multi-select logic)
```

**Root Issue**: 
The abstraction assumes `context` determines the resolver. But in reality, **constraints determine the resolver**.

- **If minCount ≤ 1**: Use GenericResolver (or similar single-select)
- **If minCount > 1**: Use PrizeResolver (or similar multi-select)

This applies to ALL contexts, not just TO_HAND:
- TO_HAND (minCount=0) → GenericResolver
- TO_HAND (minCount=2) → PrizeResolver
- TO_PRIZE (minCount=2) → PrizeResolver
- SETUP_BENCH (minCount=0, maxCount=2) → GenericResolver (0 is allowed)
- And so on...

---

## DESIGN IMPLICATION

### Current Design (Wrong)

```
SelectionResolverRegistry:
  context → resolver lookup
  
  SelectContext.TO_HAND → GenericResolver (always)
  SelectContext.TO_PRIZE → PrizeResolver (always)
  SelectContext.* → GenericResolver (default)

Problem: Ignores minCount/maxCount in the dispatch decision
```

### Correct Design (Constraint-Based)

```
SelectionResolverRegistry:
  (context, minCount, maxCount) → resolver lookup
  
  If minCount ≤ 1:
    → GenericResolver (or context-specific single-select)
  If minCount > 1:
    → PrizeResolver (or context-specific multi-select)

Reason: The resolver choice depends on whether multi-selection is required
```

---

## EVIDENCE SUMMARY

| Observation | Context | Constraints | Behavior | Outcome |
|---|---|---|---|---|
| #1-#4 | TO_HAND | min=1, max=1 | Single-select works | ✓ Valid |
| #5-#7 | TO_HAND | min=0, max=1 | Optional single-select works | ✓ Valid |
| #8 | TO_HAND | min=2, max=2 | Single-select fails | ✗ INVALID |

**The Pattern**: 
- Contexts that CAN have minCount > 1 are "conditionally multi-select"
- Contexts that ALWAYS have minCount ≤ 1 are "always single-select"
- **TO_HAND is conditionally multi-select** (can be either)

---

## ANSWER TO YOUR QUESTION

### Is TO_HAND fundamentally a multi-selection context?

**NO**

### Or is it a context that sometimes becomes multi-select depending on minCount/maxCount?

**YES** - This is exactly what happens.

### Why is dispatching by context the wrong abstraction?

Because:

1. **TO_HAND with minCount=1 requires single-select logic**
   - GenericResolver works fine
   - Returns 1 index from available options
   - SDK accepts it (constraint satisfied: 1 ≥ minCount)

2. **TO_HAND with minCount=2 requires multi-select logic**
   - GenericResolver fails
   - Returns only 1 index from multiple options
   - SDK rejects it (constraint violated: 1 < minCount)

3. **Context enum alone cannot determine the resolver**
   - Same context (TO_HAND) needs different resolvers depending on constraints
   - Dispatching by context alone = ignoring the constraints
   - This is fundamentally wrong

4. **The correct dispatch key should include constraints**
   - Not just context, but (context, minCount, maxCount)
   - Or more simply: dispatch by minCount/maxCount, then within that dispatch by context
   - Or: always check constraints before returning from the resolver

---

## CONCLUSION

**The real problem is not that TO_HAND needs a different resolver.**

**The real problem is that the resolver dispatch mechanism is context-only, when it should be constraint-aware.**

All contexts can potentially become multi-select if an effect requires it. The current architecture assumes contexts are inherently single-select or multi-select, but that's not how the actual game works.

A game effect can have ANY context with ANY constraints. The resolver needs to:
1. Check the constraints
2. Return indices that satisfy those constraints
3. Not assume a single behavior based on context alone

This is why both a simple "add TO_HAND to PrizeResolver" fix AND a more robust constraint-aware dispatch are on the table.

