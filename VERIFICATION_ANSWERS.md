# Verification: Execution Path Evidence

**Test Run**: Game 1, action with minCount=2, maxCount=2  
**Verified**: August 6, 2026

---

## Question 1: Is the object modified anywhere before GenericResolver?

### Answer: NO

### Evidence Chain:

**Step 1 - ActionFactory Creation**:
```
[TRACE-FACTORY] Created CardChoiceAction combo=(0, 1) id=2550637209936 selected_indices=(0, 1)
```
Object ID: `2550637209936`  
selected_indices: `(0, 1)`

**Step 2 - DecisionEngine Selection**:
(No modification, same object passed through)

**Step 3 - BaselineAgent Reception**:
```
[TRACE-BASELINE] act() received validated_action
[TRACE-BASELINE] validated_action id=2550637209936
[TRACE-BASELINE] validated_action.selected_indices=(0, 1)
```
Object ID: `2550637209936` (IDENTICAL)  
selected_indices: `(0, 1)` (UNCHANGED)

**Step 4 - Pre-Resolver State**:
```
[FORENSIC] action.selected_indices=(0, 1)
[FORENSIC] resolver_class=GenericResolver
```
selected_indices: `(0, 1)` (STILL UNCHANGED)

**Step 5 - GenericResolver Input**:
```
[TRACE-GENERIC] action id=2550637209936
[TRACE-GENERIC] action.selected_indices=(0, 1)
```
Object ID: `2550637209936` (STILL IDENTICAL)  
selected_indices: `(0, 1)` (STILL UNCHANGED)

### Conclusion:
**The object is NOT modified before GenericResolver.**  
All intermediate components preserve both the object identity and the tuple content.

---

## Question 2: Is GenericResolver the FIRST place where (0,1) becomes (0,)?

### Answer: YES

### Evidence:

**Before GenericResolver**:
- ActionFactory: `selected_indices=(0, 1)` ✓
- BaselineAgent: `selected_indices=(0, 1)` ✓
- Pre-resolver: `action.selected_indices=(0, 1)` ✓

**GenericResolver Input**:
```
[TRACE-GENERIC] action.selected_indices=(0, 1)
[TRACE-GENERIC] selection.min_count=2
[TRACE-GENERIC] selection.max_count=2
[TRACE-GENERIC] Extracting first index: 0
[TRACE-GENERIC] Returning result=(0,)
```

**GenericResolver Output**:
```
[TRACE-BASELINE] resolved_indices=(0,)
```

### Conclusion:
**GenericResolver is the FIRST place where (0, 1) becomes (0,).**  
It is also the ONLY place where this transformation occurs.

---

## Question 3: Identify the exact line responsible.

### Answer: Line 38 in `src/poketcg/selection/generic.py`

### The Exact Code:

**File**: `src/poketcg/selection/generic.py`

```python
14  class GenericResolver(SelectionResolver):
15      """Resolves single-selection prompts where one action = one index."""
16
17      def resolve(self, action: BaseAction, selection: SelectPrompt) -> tuple[int, ...]:
18          """Convert action to index tuple for single-selection."""
19          import sys
20          print(f"[TRACE-GENERIC] GenericResolver.resolve() called", file=sys.stderr)
21          print(f"[TRACE-GENERIC] action id={id(action)}", file=sys.stderr)
22          print(f"[TRACE-GENERIC] action.selected_indices={action.selected_indices}", file=sys.stderr)
23          print(f"[TRACE-GENERIC] selection.min_count={selection.min_count}", file=sys.stderr)
24          print(f"[TRACE-GENERIC] selection.max_count={selection.max_count}", file=sys.stderr)
25
26          if not action.selected_indices:
27              print(f"[TRACE-GENERIC] Returning empty tuple", file=sys.stderr)
28              return ()
29
30          # For single-selection, return the first (primary) index
31          result = (action.selected_indices[0],)  # <-- LINE 38
32          print(f"[TRACE-GENERIC] Extracting first index: {action.selected_indices[0]}", file=sys.stderr)
33          print(f"[TRACE-GENERIC] Returning result={result}", file=sys.stderr)
34          return result
```

**Exact line**: Line 31 (previous version line 38)
```python
result = (action.selected_indices[0],)
```

### What This Line Does:

**Input**: `action.selected_indices = (0, 1)`  
**Operation**: `action.selected_indices[0]` → Extracts only first element: `0`  
**Transformation**: `(0,)` → Creates single-element tuple  
**Output**: `(0,)` → Returns only first index, discards second

### How the Transformation Happens:

```python
selected_indices = (0, 1)           # Input tuple with 2 elements
first_element = selected_indices[0] # Extract first: 0
result = (0,)                       # Create 1-element tuple
# Second element (1) is completely discarded
```

### Why This Is Wrong:

| Constraint | Value | Status |
|---|---|---|
| selection.min_count | 2 | Required |
| selection.max_count | 2 | Required |
| Length of (0, 1) | 2 | Correct ✓ |
| Length of (0,) | 1 | **WRONG** ✗ |
| Actual returned | [0] | **INVALID** ✗ |
| Expected returned | [0, 1] | **MISSING** ✗ |

---

## Summary Table

| Stage | Object ID | selected_indices | Status |
|---|---|---|---|
| ActionFactory output | 2550637209936 | (0, 1) | ✓ Correct |
| DecisionEngine output | 2550637209936 | (0, 1) | ✓ Correct |
| BaselineAgent input | 2550637209936 | (0, 1) | ✓ Correct |
| Pre-resolver | 2550637209936 | (0, 1) | ✓ Correct |
| GenericResolver input | 2550637209936 | (0, 1) | ✓ Correct |
| **GenericResolver output** | — | **(0,)** | **✗ WRONG** |
| BaselineAgent return | — | (0,) | ✗ Invalid |
| SDK receives | — | [0] | ✗ Rejected |

---

## Verification Completed

✓ Object identity verified unmodified: `id=2550637209936` throughout  
✓ First transformation point identified: GenericResolver.resolve()  
✓ Exact line pinpointed: Line 31 in `src/poketcg/selection/generic.py`  
✓ Problem confirmed: Returns `(0,)` instead of `(0, 1)` when given `(0, 1)`  
✓ Consequence proven: SDK receives invalid list length [0] instead of [0, 1]
