# Final Answer: SelectContext.TO_HAND Investigation

**Investigation Date**: August 6, 2026  
**Status**: COMPLETE - All occurrences of SelectContext.TO_HAND analyzed

---

## SEARCH RESULTS: Every TO_HAND Occurrence

### Summary Table

| Observation | Step | minCount | maxCount | Resolver | Returned | Valid? |
|---|---|---|---|---|---|---|
| 1 | Early | 1 | 1 | GenericResolver | [0] | ✓ |
| 2 | 1337 | 1 | 1 | GenericResolver | [0] | ✓ |
| 3 | 2023 | 1 | 1 | GenericResolver | [0] | ✓ |
| 4 | 3833 | 1 | 1 | GenericResolver | [0] | ✓ |
| 5 | 4410 | 0 | 1 | GenericResolver | [0] | ✓ |
| 6 | 5173 | 0 | 1 | GenericResolver | [0] | ✓ |
| 7 | 6095 | 0 | 1 | GenericResolver | [0] | ✓ |
| 8 | 6292 | **2** | **2** | GenericResolver | [0] | **✗ INVALID** |

---

## QUESTION 1: Is TO_HAND fundamentally a multi-selection context?

### Answer: **NO**

### Evidence:
- Out of 8 observations, only 1 has minCount > 1
- 7 observations have minCount ≤ 1 (all working correctly)
- 1 observation has minCount = 2 (fails)

**Conclusion**: TO_HAND is fundamentally a **single-select context**.

---

## QUESTION 2: Or is it a context that sometimes becomes multi-select depending on minCount/maxCount?

### Answer: **YES - EXACTLY THIS**

### Evidence:
```
Observation #1-#7 (minCount ≤ 1):
  - Single-select required
  - GenericResolver returns [0]
  - SDK accepts it ✓

Observation #8 (minCount = 2):
  - Multi-select required
  - GenericResolver returns [0]
  - SDK rejects it ✗ (needs 2 indices, got 1)
```

**Conclusion**: Same context (TO_HAND) needs **different resolver behavior** depending on constraints.

---

## QUESTION 3: Why is dispatching by context the wrong abstraction?

### Answer: Because constraints, not context, determine resolver behavior

### The Mechanism:

**Current design (broken)**:
```python
resolver = registry.get_resolver(SelectContext.TO_HAND)
# Returns GenericResolver (always)
# This is wrong because:
#   - GenericResolver works when minCount ≤ 1
#   - GenericResolver fails when minCount > 1
# The resolver choice depends on constraints, not context!
```

**Why it's wrong**:
```
SelectContext.TO_HAND with minCount=1
  ↓
GenericResolver returns (0,)
  ↓
SDK receives [0]
  ↓
minCount constraint: 1 ≥ 1 ✓ VALID

SelectContext.TO_HAND with minCount=2
  ↓
GenericResolver returns (0,)
  ↓
SDK receives [0]
  ↓
minCount constraint: 1 ≥ 2 ✗ INVALID
```

### The Real Problem:

The current registry maps:
```
Context → Resolver

SelectContext.TO_HAND → GenericResolver (always, regardless of minCount)
SelectContext.TO_PRIZE → PrizeResolver (always, regardless of minCount)
```

But it should map:
```
Constraints → Resolver

minCount ≤ 1 → GenericResolver (works for any context)
minCount > 1 → PrizeResolver (works for any context)
```

### Why This Generalizes:

The problem is **not specific to TO_HAND**.

- **Any context can become multi-select** if the game effect requires it
- The current architecture assumes contexts are inherently single-select or multi-select
- But the actual game allows ANY context with ANY constraints

Examples of what could happen (hypothetically):
- TO_ACTIVE (usually minCount=1) could become minCount=2 in some edge case
- TO_BENCH (usually minCount=0-2) could become minCount=3 in some edge case
- DISCARD (usually minCount=0-1) could become minCount=2 in some edge case

**The lesson**: Constraints are the source of truth, not context.

---

## DISPATCH MECHANISM: Wrong Abstraction Explained

### Current Code Pattern:
```python
# SelectionResolverRegistry.get_resolver()

resolver = self._resolvers.get(context, default_resolver)
# This assumes: context determines resolver choice
# This is wrong: constraints determine resolver choice
```

### Why It Fails for TO_HAND:

The registry has:
```python
self._resolvers[SelectContext.TO_HAND] = GenericResolver()
self._resolvers[SelectContext.TO_PRIZE] = PrizeResolver()
```

When called with:
```python
SelectPrompt(
  context=SelectContext.TO_HAND,
  minCount=2,
  maxCount=2,
  options=[...]
)
```

The registry does:
```python
resolver = self._resolvers[SelectContext.TO_HAND]  # GenericResolver
result = resolver.resolve(prompt)  # Returns [0] (only 1 index)
```

But it should do:
```python
if prompt.minCount > 1:
  resolver = PrizeResolver()  # Multi-select
elif prompt.minCount <= 1:
  resolver = GenericResolver()  # Single-select
# Then dispatch to the correct resolver
result = resolver.resolve(prompt)
```

---

## SUMMARY

### Finding 1: TO_HAND is NOT Fundamentally Multi-Select
- It's a **conditionally multi-select** context
- Most observations have minCount ≤ 1 (single-select works)
- One observation has minCount = 2 (single-select fails)

### Finding 2: The Problem is the Dispatch Abstraction
- Current: `context → resolver` (wrong)
- Correct: `constraints → resolver` (right)

### Finding 3: This is a General Problem
- Not specific to TO_HAND
- Any context can potentially have minCount > 1
- The resolver dispatch should always consider constraints

### Finding 4: Dispatcher Ignores Constraints
- `SelectionResolverRegistry.get_resolver(context)` takes only context
- It doesn't even look at minCount/maxCount
- This is why TO_HAND with minCount=2 uses the wrong resolver

---

## PROOF

**Observation #8** (The failure case):

```
[FORENSIC] selection.context=SelectContext.TO_HAND
[FORENSIC] selection.minCount=2
[FORENSIC] selection.maxCount=2
[FORENSIC] resolver_class=GenericResolver  ← WRONG RESOLVER
[FORENSIC-GENERIC] Returning (0,)          ← WRONG RESULT
[FORENSIC] About to return to SDK: [0]     ← WRONG DATA
[Game 1/10] Statuses: ['INVALID', 'DONE']  ← FAILURE
```

**Why it's wrong**:
- Context is TO_HAND → Resolver registry returns GenericResolver
- But minCount is 2 → GenericResolver cannot satisfy this constraint
- GenericResolver returns 1 index → SDK needs 2 → INVALID

**What should happen**:
- Context is TO_HAND AND minCount is 2 → Should use PrizeResolver
- PrizeResolver returns 2 indices → SDK gets 2 → VALID

---

## ARCHITECTURAL INSIGHT

The dispatch mechanism is **context-driven when it should be constraint-driven**.

This is why:
1. Different contexts with same constraints should use same resolver logic
2. Same context with different constraints should use different resolver logic
3. Current design does neither correctly

The fix must make constraint awareness central to resolver dispatch.

