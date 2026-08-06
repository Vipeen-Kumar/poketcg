# CRITICAL BUG VERIFICATION

**Date**: August 6, 2026  
**Status**: BUG CONFIRMED - Breaking assumption in BaselineAgent._validate_action_legality()

---

## EXECUTION TRACE

### Input State
```
legal_actions = [
    Action(0, selected_indices=(0,1)),   # position 0
    Action(1, selected_indices=(0,2)),   # position 1
    Action(2, selected_indices=(1,2)),   # position 2
]

DecisionEngine returns: legal_actions[2]
  i.e., Action(2, selected_indices=(1,2))
```

### Step 1: ActionFactory Generated Actions ✓

**File**: `src/poketcg/actions/factory.py`

ActionFactory correctly generated:
```python
Action(selected_indices=(0,1))
Action(selected_indices=(0,2))
Action(selected_indices=(1,2))
```

Each action is a valid combination with `.action_index` property returning first index.

---

### Step 2: DecisionEngine Chose Action ✓

**File**: `src/poketcg/decision/engine.py`

DecisionEngine correctly returns ONE action from context.legal_actions:
```python
# Pseudo-code
for rule in rules:
    result = rule.evaluate(context)
    if result.passed:
        return result.selected_action  # Returns legal_actions[2]

# Returns:
selected_action = legal_actions[2]  # Action(selected_indices=(1,2))
```

**Data at this point**:
```
selected_action.selected_indices = (1, 2)
selected_action.action_index = 1  # (property returns first index)
```

---

### Step 3: BaselineAgent._validate_action_legality() ⚠️ CRITICAL BUG

**File**: `src/poketcg/agent/baseline.py`, lines 206-250

#### Layer 1: Null check ✓
```python
if selected_action is None:
    return artifacts.context.legal_actions[0]

# PASSES - action is not None
```

#### Layer 2: Bounds check on action_index ✗✗✗ BUG

```python
action_index = selected_action.action_index  # = 1
# ^^^ THIS IS THE BUG LOCATION

if action_index < 0 or action_index >= len(artifacts.context.legal_actions):
    # action_index = 1
    # len(legal_actions) = 3
    # 0 <= 1 < 3 => PASSES
    return artifacts.context.legal_actions[0]

# PASSES - index is in bounds
```

**THE ASSUMPTION**: Line 231-232 assumes:
```python
legal_actions[action_index] == selected_action
```

**In our example**:
- `action_index = 1` (first index of combination action)
- `legal_actions[1]` = Action(1, selected_indices=(0,2))
- `selected_action` = Action(2, selected_indices=(1,2))
- **MISMATCH!**

#### Layer 3: Identity check ✗ CATCHES THE BUG (but with wrong fallback)

```python
legal_action_at_index = artifacts.context.legal_actions[action_index]
#                                                         ^^^^ = 1
# = Action(1, selected_indices=(0,2))  # WRONG ACTION!

if selected_action is not legal_action_at_index:
    # True: Action(2,...) is not Action(1,...)
    
    if not (hasattr(selected_action, 'action_index') and 
           selected_action.action_index == legal_action_at_index.action_index and
           type(selected_action) == type(legal_action_at_index)):
        #   True (1 == 1) BUT
        # ^^^^^^^ FALSE (type match) - different instances
        # Actually: selected_action.action_index == 1
        #           legal_action_at_index.action_index == 0 (first of (0,2))
        # So: 1 == 0? FALSE
        
        # This condition is TRUE, so we return fallback:
        return artifacts.context.legal_actions[0]  # WRONG ACTION!
```

---

### **THE BUG REVEALED**

**File**: `src/poketcg/agent/baseline.py`  
**Lines**: 231-232 (bounds check) and 239-243 (identity fallback)

**Problem**:
```python
legal_action_at_index = artifacts.context.legal_actions[action_index]
```

This line **assumes** `action_index` is the position in `legal_actions`, but for combination actions:
- `action_index = 1` (first selected index from (1,2))
- `legal_actions[1]` = Action with indices (0,2) from position 1 in array
- **DIFFERENT ACTIONS!**

**Consequence**:
1. Validation incorrectly fetches wrong action from array
2. Identity check fails
3. Falls back to `legal_actions[0]` - selecting WRONG action
4. Agent returns indices from WRONG combination
5. Game receives incorrect move

---

### Step 4: SelectionResolver (Never Reached Due to Fallback) ✗

**File**: `src/poketcg/selection/resolver.py`

If bug didn't exist, would execute:
```python
resolved_indices = self._selection_resolver.resolve(
    validated_action,
    observation.selection
)
# Would correctly return (1, 2)
```

**But instead**:
```python
# validation returned legal_actions[0] = Action(selected_indices=(0,1))
resolved_indices = self._selection_resolver.resolve(
    Action(selected_indices=(0,1)),  # WRONG ACTION!
    observation.selection
)
# Returns (0, 1) instead of (1, 2)
```

---

### Step 5: Serialization to ActionSelection ✗

**File**: `src/poketcg/agent/baseline.py`, line 119

```python
return ActionSelection(selected_option_indices=(0, 1))
# WRONG! Should be (1, 2)
```

**What SDK receives**:
```
[0, 1]  # Wrong combination!
```

---

## ROOT CAUSE ANALYSIS

### The Broken Assumption

**Line 232 in baseline.py**:
```python
legal_action_at_index = artifacts.context.legal_actions[action_index]
```

This assumes: **action_index is the position in legal_actions**

But for combination actions:
- `action_index` is the **first selected index** from `selected_indices`
- It is NOT the position in the `legal_actions` array

### When This Works (Single-select)

Single-selection actions have special property:
```python
# When ActionFactory creates single actions:
for i, option in enumerate(options):
    action = build_action(i, ...)
    actions.append(action)

# selected_indices = (i,)
# action_index = i
# legal_actions[i] contains Action(selected_indices=(i,))
# legal_actions[i].action_index == i
# MATCH: legal_actions[i].action_index == action_index ✓
```

### Why It Breaks (Multi-select)

```python
# When ActionFactory creates combinations:
legal_actions = [
    Action(selected_indices=(0,1)),   # legal_actions[0]
    Action(selected_indices=(0,2)),   # legal_actions[1]
    Action(selected_indices=(1,2)),   # legal_actions[2]
]

# If DecisionEngine returns legal_actions[2]:
selected_action = legal_actions[2]  # selected_indices=(1,2)
selected_action.action_index = 1    # FIRST index

# Validation does:
legal_action_at_index = legal_actions[1]  # WRONG!
# legal_actions[1] has selected_indices=(0,2)
# So legal_action_at_index.action_index = 0

# Comparison: 1 == 0? FALSE
# MISMATCH ✗
```

---

## EXACT BUG LOCATION

**File**: `src/poketcg/agent/baseline.py`

**Lines 231-243**:
```python
231     action_index = selected_action.action_index
232
233     if action_index < 0 or action_index >= len(artifacts.context.legal_actions):
234         # Invalid index - use first legal action
235         if artifacts.context.legal_actions:
236             return artifacts.context.legal_actions[0]
237         raise RuntimeError(...)
238
239     # Layer 3: Identity check
240     legal_action_at_index = artifacts.context.legal_actions[action_index]
        # ^^^ BUG: Assumes action_index is array position
        # This is only true for single-selection!
242
243     if selected_action is not legal_action_at_index:
```

**The buggy code treats `action_index` as an array position when it's actually "first selected index".**

---

## EVIDENCE SUMMARY

### What Should Happen

```
Input:
  legal_actions = [Action((0,1)), Action((0,2)), Action((1,2))]
  selected_action = legal_actions[2] = Action((1,2))

Expected:
  Validation accepts it (it's in legal_actions)
  SelectionResolver returns (1, 2)
  SDK receives [1, 2] ✓ CORRECT

Actual:
  action_index = 1 (first index from (1,2))
  legal_actions[1] = Action((0,2)) - WRONG!
  Validation rejects with identity mismatch
  Falls back to legal_actions[0] = Action((0,1))
  SelectionResolver returns (0, 1)
  SDK receives [0, 1] ✗ WRONG
```

### Verification of the Assumption

The code explicitly assumes `action_index` maps to `legal_actions` position by:
1. Using `action_index` as array index
2. Comparing `selected_action` with `legal_actions[action_index]`
3. Expecting object identity or equality

This works for single-select but **fails for combinations**.

---

## CONCLUSION

**Critical bug found in BaselineAgent._validate_action_legality()**

The validation logic breaks when ActionFactory generates combination actions because it incorrectly assumes that `action.action_index` is the position in `legal_actions`.

For combination actions:
- `action.action_index` = first selected index (used for tie-breaking)
- Position in `legal_actions` = array index (unrelated to selected_indices)

**This bug will cause**:
- ✗ Correct actions to be rejected
- ✗ Wrong actions to be selected as fallback
- ✗ Invalid moves sent to SDK
- ✗ Games marked INVALID

**The bug must be fixed before implementation is complete.**

