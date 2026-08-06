# Multi-Selection Protocol: Official SDK Proof

## Executive Finding: Answer is A) ✅

**When minCount = 2, the environment expects the agent to return [0, 1] ONCE, not in multiple calls.**

---

## Direct Evidence from Official SDK

### Source 1: Official SDK Sample Agents
**File**: `kaggle_environments/envs/cabt/cabt.py` (Lines 73-82)

```python
def random_agent(obs: dict) -> list[int]:
    if obs["select"] == None:
        return deck
    return random.sample(list(range(len(obs["select"]["option"]))), obs["select"]["maxCount"])


def first_agent(obs: dict) -> list[int]:
    if obs["select"] == None:
        return deck
    return list(range(obs["select"]["maxCount"]))
```

**Critical Analysis**:

#### Line 76 (random_agent):
```python
return random.sample(list(range(len(obs["select"]["option"]))), obs["select"]["maxCount"])
```
- **What it does**: Returns a random selection of `maxCount` indices from available options
- **When maxCount=2**: Returns 2 random distinct indices, e.g., `[0, 2]` or `[1, 2]`
- **Return type**: `list[int]` containing exactly `maxCount` elements
- **Frequency**: Returns this list ONCE per `obs["select"]` call

#### Line 82 (first_agent):
```python
return list(range(obs["select"]["maxCount"]))
```
- **What it does**: Returns the first N indices where N = `maxCount`
- **When maxCount=1**: Returns `[0]`
- **When maxCount=2**: Returns `[0, 1]`
- **When maxCount=3**: Returns `[0, 1, 2]`
- **Return type**: `list[int]` containing exactly `maxCount` elements
- **Frequency**: Returns this list ONCE per selection

### Key Evidence Points:

1. **Return Type Declaration**: Both agents are declared as `-> list[int]`
   - Not `-> int` (single element)
   - Not `-> generator` (streaming responses)
   - Explicitly `list[int]` (array of integers)

2. **Return Value Structure**:
   - `random.sample(..., obs["select"]["maxCount"])` returns a **list**
   - `list(range(...))` returns a **list**
   - Both return exactly one list per call

3. **Single Call Semantics**:
   - `random_agent()` is called once per selection
   - `first_agent()` is called once per selection
   - Neither is called multiple times for the same selection prompt

---

## How Multi-Selection Works (Official Protocol)

### Scenario: Prize Card Selection with minCount=2, maxCount=2, 3 options available

**Example from first_agent**:
```python
obs["select"]["maxCount"] = 2
obs["select"]["option"] = [option0, option1, option2]  # 3 prize cards

# Agent called once
returned_list = first_agent(obs)  # Called exactly ONCE
# Returns: [0, 1]
```

**Example from random_agent**:
```python
obs["select"]["maxCount"] = 2
obs["select"]["option"] = [option0, option1, option2]  # 3 prize cards

# Agent called once
returned_list = random_agent(obs)  # Called exactly ONCE
# Could return: [0, 2] or [1, 2] or [0, 1] - any valid 2-element combination
```

**What is passed to battle_select()**:
```python
battle_select([0, 1])  # Called once with the full list
# NOT:
# battle_select([0])  then later battle_select([1])
```

---

## Proof from Official cabt.py Wrapper

**File**: `kaggle_environments/envs/cabt/cabt.py` (Lines 52-125)

```python
def interpreter(state, env):
    # ... [game setup] ...
    else:
        error = False
        select_player = Battle.obs["current"]["yourIndex"]
        
        try:
            battle_select(state[select_player].action)  # <-- Single call with full action list
        except:
            state[select_player].status = "INVALID"
            error = True
```

**Key Point**: 
- Line 65: `battle_select()` is called **exactly once** per selection
- `state[select_player].action` is the **complete action** from the agent
- The action is expected to be a `list[int]` meeting the minCount/maxCount constraints

---

## Proof from battle_select() Implementation

**File**: `kaggle_environments/envs/cabt/cg/game.py` (Lines 39-52)

```python
def battle_select(select_list: list[int]) -> dict:
    """Select option.

    Args:
        select_list:  <-- Expects a FULL list in one call

    Returns:
        dict: Next observation.
    """
    if not isinstance(select_list, list) or not all(isinstance(i, int) for i in select_list):
        raise ValueError("select_list is not list[int]")
    arg = (ctypes.c_int * len(select_list))(*select_list)
    err = lib.Select(Battle.battle_ptr, arg, len(select_list))
    if err != 0:
        # ... error handling ...
        raise IndexError()
    return _get_battle_data()
```

**Analysis**:
- Parameter name: `select_list` (not `select_item` or `select_index`)
- Type: `list[int]` (collection, not single value)
- Line 46: Validates that ALL elements are integers
- Line 47: Converts ENTIRE list to C++ array in ONE operation
- Line 48: Calls C++ with the FULL length of the list
- No loop, no multiple calls, **single call semantics**

---

## Cross-Reference: Official Documentation

**File**: `docs/environment.md` (Lines 536-554)

```markdown
### `minCount`, `maxCount`

- What they represent: lower and upper bounds on how many option indices must be returned.
- Important note: The agent returns a **list of option indices**, and its length must satisfy these bounds.
```

**"the agent returns a list"** - singular "returns", singular "list", not "multiple lists" or "streaming indices"

---

## Definitive Answer

### Question: When minCount = 2, does the environment expect:
- **A) agent returns [0,1] once** ✅ **YES - PROVEN**
- **B) agent returns [0] then later [1]** ❌ NO
- **C) another protocol** ❌ NO

### Proof Summary:

| Evidence | Finding |
|----------|---------|
| **first_agent source** | Returns `list(range(maxCount))` = `[0,1]` in single call |
| **random_agent source** | Returns `random.sample(..., maxCount)` = `[0,2]` in single call |
| **Return type annotation** | Both: `-> list[int]` (not generator, not stream) |
| **battle_select() signature** | Accepts `select_list: list[int]` - full list in one call |
| **interpreter() usage** | Calls `battle_select(state[select_player].action)` once |
| **C++ validation** | `lib.Select(battle_ptr, arg, len(select_list))` - validates full length |
| **Official docs** | "agent returns a list of option indices" (singular) |

---

## What This Means for ActionFactory

When implementing multi-selection support:

```python
# Current (WRONG for minCount != 1):
from_selection() → creates N single-select actions
agent returns: 0 (single integer)
wrapper sends: [0] to battle_select()
# minCount=2: FAILS ❌

# Correct (for minCount > 1):
from_selection() → creates multi-select combination actions
agent returns: [0, 1] (list of integers)  # <-- This is the key difference
wrapper sends: [0, 1] to battle_select()  # Same list passed through
# minCount=2: SUCCEEDS ✅
```

**The protocol change**: Agent must return `list[int]` when handling multi-select contexts, not a single integer.

---

## Implementation Readiness: CONFIRMED ✅

**Based on this analysis, we can now safely implement multi-selection support:**

1. ✅ Multi-selection protocol is: **single call with full list**
2. ✅ Protocol matches SDK sample agents exactly
3. ✅ battle_select() explicitly expects this format
4. ✅ No streaming, no multiple calls, no state management needed
5. ✅ Minimal ActionFactory change needed

**Ready to proceed with implementation.**
