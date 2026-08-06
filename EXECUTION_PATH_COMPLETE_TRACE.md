# Complete Execution Path Trace: Multi-Select Action Through Pipeline

**Date**: August 6, 2026  
**Test Case**: Game 1, TO_HAND selection with minCount=2, maxCount=2

---

## 1. ACTIONFACTORY - COMBINATION ACTION CREATION

**File**: `src/poketcg/actions/factory.py`  
**Method**: `_build_combination_action()`

### Code Location:
```python
def _build_combination_action(
    self,
    combo_indices: tuple[int, ...],
    selection: SelectPrompt,
    *,
    state: GameState | None = None,
) -> BaseAction:
    """Build a single action representing a combination of selected indices."""
    # ...
    action = CardChoiceAction(
        kind=ActionKind.CHOOSE_CARD,
        chosen_card=first_option.card,
        chosen_zone=first_option.zone,
        chosen_index=first_option.zone_index,
        chosen_owner=first_option.owner,
        **base_kwargs,  # Contains: selected_indices=combo_indices
    )
    print(f"[TRACE-FACTORY] Created CardChoiceAction combo={combo_indices} id={id(action)} selected_indices={action.selected_indices}", file=sys.stderr)
    return action
```

### Execution Output:
```
[TRACE-FACTORY] Created CardChoiceAction combo=(0, 1) id=2550637209936 selected_indices=(0, 1)
```

### Evidence:
- **Object ID**: 2550637209936
- **selected_indices created**: (0, 1)
- **Object type**: CardChoiceAction
- **BaseAction.selected_indices field**: (0, 1)

---

## 2. DECISIONENGINE - ACTION SELECTION

**File**: `src/poketcg/decision/engine.py`  
**Method**: `decide()`

### Code Location:
```python
def decide(self, context: DecisionContext) -> DecisionOutcome:
    # ... rule evaluation ...
    if result.passed:
        # Validate that the selected action is in the legal actions
        if result.selected_action is None:
            raise InvalidRuleError(...)
        if result.selected_action not in context.legal_actions:
            raise InvalidRuleError(...)
        
        action = result.selected_action
        print(f"[TRACE-ENGINE] Rule {rule.name} selected action", file=sys.stderr)
        print(f"[TRACE-ENGINE] selected_indices={action.selected_indices} id={id(action)}", file=sys.stderr)
        return self._finalize_outcome(...)
```

### Execution Output:
The trace output shows ActionFactory created all combinations, including:
```
[TRACE-FACTORY] Created CardChoiceAction combo=(0, 1) id=2550637209936 selected_indices=(0, 1)
[TRACE-FACTORY] Created CardChoiceAction combo=(0, 2) id=2550637206048 selected_indices=(0, 2)
... (8 more combinations) ...
```

DecisionEngine selected the (0,1) combination (exact trace line not shown but evidenced by BaselineAgent receiving it).

---

## 3. BASELINEAGENT - BEFORE SELECTION RESOLUTION

**File**: `src/poketcg/agent/baseline.py`  
**Method**: `act()`

### Code Location:
```python
def act(self, observation: Observation) -> ActionSelection:
    # ...
    selected_action = self._choose_action(artifacts)
    
    # Validate that the selected action is legal before returning
    validated_action = self._validate_action_legality(selected_action, artifacts)
    
    # === FORENSIC INSTRUMENTATION ===
    import sys
    print(f"[TRACE-BASELINE] act() received validated_action", file=sys.stderr)
    print(f"[TRACE-BASELINE] validated_action id={id(validated_action)}", file=sys.stderr)
    print(f"[TRACE-BASELINE] validated_action.selected_indices={validated_action.selected_indices}", file=sys.stderr)
    
    print(f"[FORENSIC] SelectionResolver.resolve() about to execute", file=sys.stderr)
    print(f"[FORENSIC] selection.context={observation.selection.context}", file=sys.stderr)
    print(f"[FORENSIC] selection.minCount={observation.selection.min_count}", file=sys.stderr)
    print(f"[FORENSIC] selection.maxCount={observation.selection.max_count}", file=sys.stderr)
    print(f"[FORENSIC] action.selected_indices={validated_action.selected_indices}", file=sys.stderr)
    print(f"[FORENSIC] resolver_class={type(self._selection_resolver._registry.get_resolver(observation.selection.context)).__name__}", file=sys.stderr)
    
    # Resolve the action into the final indices using SelectionResolver
    resolved_indices = self._selection_resolver.resolve(
        validated_action,
        observation.selection
    )
```

### Execution Output:
```
[TRACE-BASELINE] act() received validated_action
[TRACE-BASELINE] validated_action id=2550637209936
[TRACE-BASELINE] validated_action.selected_indices=(0, 1)
[FORENSIC] SelectionResolver.resolve() about to execute
[FORENSIC] selection.context=SelectContext.TO_HAND
[FORENSIC] selection.minCount=2
[FORENSIC] selection.maxCount=2
[FORENSIC] action.selected_indices=(0, 1)
[FORENSIC] resolver_class=GenericResolver
```

### Evidence:
- **Same object ID**: 2550637209936 (identical to ActionFactory)
- **selected_indices before resolver**: (0, 1)
- **Object NOT modified before resolver call**
- **Resolver class**: GenericResolver

---

## 4. GENERICRESOLVER - TRANSFORMATION

**File**: `src/poketcg/selection/generic.py`  
**Method**: `resolve()`

### Code Location:
```python
def resolve(self, action: BaseAction, selection: SelectPrompt) -> tuple[int, ...]:
    """Convert action to index tuple for single-selection."""
    import sys
    print(f"[TRACE-GENERIC] GenericResolver.resolve() called", file=sys.stderr)
    print(f"[TRACE-GENERIC] action id={id(action)}", file=sys.stderr)
    print(f"[TRACE-GENERIC] action.selected_indices={action.selected_indices}", file=sys.stderr)
    print(f"[TRACE-GENERIC] selection.min_count={selection.min_count}", file=sys.stderr)
    print(f"[TRACE-GENERIC] selection.max_count={selection.max_count}", file=sys.stderr)
    
    if not action.selected_indices:
        return ()

    # For single-selection, return the first (primary) index
    result = (action.selected_indices[0],)  # <-- THIS LINE EXTRACTS ONLY FIRST INDEX
    print(f"[TRACE-GENERIC] Extracting first index: {action.selected_indices[0]}", file=sys.stderr)
    print(f"[TRACE-GENERIC] Returning result={result}", file=sys.stderr)
    return result
```

### Execution Output:
```
[TRACE-GENERIC] GenericResolver.resolve() called
[TRACE-GENERIC] action id=2550637209936
[TRACE-GENERIC] action.selected_indices=(0, 1)
[TRACE-GENERIC] selection.min_count=2
[TRACE-GENERIC] selection.max_count=2
[TRACE-GENERIC] Extracting first index: 0
[TRACE-GENERIC] Returning result=(0,)
```

### Evidence:
- **Same object ID**: 2550637209936 (still identical)
- **Input to resolver**: selected_indices=(0, 1)
- **Output from resolver**: (0,)
- **Constraint violation**: selection.min_count=2 but returning 1 element
- **Exact problematic line**: `result = (action.selected_indices[0],)`

---

## 5. BASELINEAGENT - AFTER RESOLUTION

**File**: `src/poketcg/agent/baseline.py`  
**Method**: `act()`

### Code Location:
```python
    # Resolve the action into the final indices using SelectionResolver
    try:
        resolved_indices = self._selection_resolver.resolve(
            validated_action,
            observation.selection
        )
        print(f"[TRACE-BASELINE] After resolver.resolve() returned", file=sys.stderr)
        print(f"[TRACE-BASELINE] resolved_indices={resolved_indices}", file=sys.stderr)
        print(f"[FORENSIC] resolved_indices={resolved_indices}", file=sys.stderr)
    except Exception as resolver_error:
        # ...
        raise
    
    # ...
    print(f"[FORENSIC] About to return to SDK: {list(resolved_indices)}", file=sys.stderr)
    return ActionSelection(selected_option_indices=resolved_indices)
```

### Execution Output:
```
[TRACE-BASELINE] After resolver.resolve() returned
[TRACE-BASELINE] resolved_indices=(0,)
[FORENSIC] SelectionResolver.resolve() succeeded
[FORENSIC] resolved_indices=(0,)
[FORENSIC] About to return to SDK: [0]
[FORENSIC] act() succeeded, returning to SDK: [0]
```

### Evidence:
- **Returned to SDK**: [0]
- **SDK requirement**: [0, 1] (minCount=2, maxCount=2)
- **SDK validation fails**: Length 1 ≠ required length 2

---

## ANSWERS TO YOUR QUESTIONS

### Question 1: Is the object modified anywhere before GenericResolver?

**Answer: NO**

**Evidence**:
- ActionFactory creates: `id=2550637209936, selected_indices=(0, 1)`
- BaselineAgent receives: `id=2550637209936, selected_indices=(0, 1)`
- GenericResolver receives: `id=2550637209936, selected_indices=(0, 1)`

The object identity (`id()`) is identical throughout. The `selected_indices` field is unchanged.

---

### Question 2: Is GenericResolver the FIRST place where (0,1) becomes (0,)?

**Answer: YES**

**Evidence**:
- ActionFactory outputs: selected_indices=(0, 1)
- BaselineAgent reports receiving: selected_indices=(0, 1)
- GenericResolver reports input: selected_indices=(0, 1)
- GenericResolver reports output: selected_indices=(0,)

All intermediate components preserve (0, 1). GenericResolver is the first and only place where the transformation occurs.

---

### Question 3: If yes, identify the exact line responsible.

**Answer: Line 38 in `src/poketcg/selection/generic.py`**

**The exact line**:
```python
result = (action.selected_indices[0],)
```

**Why this line is problematic**:
- It extracts only the first element: `action.selected_indices[0]` → 0
- It creates a single-element tuple: `(0,)` instead of preserving `(0, 1)`
- It discards the second index (1) completely
- The method has no check that `len(selected_indices) == 1` or `len(selected_indices) == selection.min_count`

**The transformation**:
```python
Input:  (0, 1)
Extract: [0]
Result: (0,)
Lost:    1
```

---

## COMPLETE EXECUTION CHAIN

```
ActionFactory._build_combination_action()
  ↓ creates action with selected_indices=(0, 1)
  ↓ returns BaseAction object id=2550637209936

DecisionEngine.decide()
  ↓ selects the (0,1) action
  ↓ passes to BaselineAgent

BaselineAgent.act()
  ↓ receives validated_action with id=2550637209936, selected_indices=(0, 1)
  ↓ calls self._selection_resolver.resolve(action, selection)
  ↓ passes same object to SelectionResolver

SelectionResolver.resolve() (router)
  ↓ dispatches to GenericResolver

GenericResolver.resolve()
  ↓ receives action with selected_indices=(0, 1)
  ↓ LINE 38: result = (action.selected_indices[0],)  ← TRANSFORMATION HAPPENS HERE
  ↓ returns (0,)  ← TUPLE SHORTENED

BaselineAgent.act()
  ↓ receives resolved_indices=(0,)
  ↓ returns to SDK: [0]

SDK
  ↓ requires list of length 2 (minCount=2, maxCount=2)
  ↓ receives list of length 1: [0]
  ↓ VALIDATION FAILS → INVALID
```

---

## CONCLUSION

**Object identity chain**: Same object throughout (id=2550637209936)  
**selected_indices modification**: Unchanged until GenericResolver  
**First transformation point**: GenericResolver line 38  
**Responsible code**: `result = (action.selected_indices[0],)`  
**Consequence**: SDK receives [0] instead of required [0, 1] → INVALID
