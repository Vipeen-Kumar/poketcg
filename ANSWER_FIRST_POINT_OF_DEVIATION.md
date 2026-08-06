# Answer: What is the FIRST point where our output differs from what the SDK expects?

---

## THE ANSWER

**Location**: `GenericResolver.resolve()` method, line 38 in `src/poketcg/selection/generic.py`

**Specific line**:
```python
result = (action.selected_indices[0],)
return result
```

**Input**:
- `action.selected_indices = (0, 1)`
- `selection.min_count = 2`
- `selection.max_count = 2`

**What we produce**: `(0,)` → serialized to SDK as `[0]`

**What the SDK expects**: `(0, 1)` → serialized to SDK as `[0, 1]`

**Why it fails**: 
- SDK receives list of length 1
- SDK requires list of length 2 (minCount=2, maxCount=2)
- SDK rejects: "Selection length does not match constraints"
- Game ends: INVALID

---

## EVIDENCE

**From debug trace at Step 82 (Game 5, Turn 25)**:

```
[FORENSIC] action.selected_indices=(0, 1)
[FORENSIC] resolver_class=GenericResolver
[FORENSIC-GENERIC] GenericResolver.resolve() called
[FORENSIC-GENERIC] selected_indices=(0, 1)
[FORENSIC-GENERIC] minCount=2
[FORENSIC-GENERIC] maxCount=2
[FORENSIC-GENERIC] Returning (0,)
[FORENSIC] About to return to SDK: [0]
```

The resolver receives `(0, 1)` but returns `(0,)`.

This is the first and only point where our output diverges from SDK expectations.
