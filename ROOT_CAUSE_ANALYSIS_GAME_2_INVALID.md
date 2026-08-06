# Root Cause Analysis: Game 2 INVALID Status

## Executive Summary

**Root Cause Identified**: The agent returned a single-element list `[0]` for a selection context that requires exactly 2 selections (`minCount=2, maxCount=2`).

**Location**: Turn 16, Player 1 (playerIndex=1), Selection Type 1 (prize card selection), Context 7

**Proof Level**: CONFIRMED from official SDK code and specifications

---

## Part 1: Evidence from Game 2 Replay

### From Trace Extraction
```
Turn: 16
Player Index: 1 (yourIndex=1 - Player 1 is the one to act)
Selection Type: 1 (CARD_SELECTION - prize cards)
Selection Context: 7 (PRIZE_SELECTION - selecting prize cards)
minCount: 2 (MUST select exactly 2)
maxCount: 2 (MUST select exactly 2)
Raw select.option: 3 options (indices 0, 1, 2)
```

### What the Agent Returned
```
Returned action: [0]
Length: 1
Expected: 2 indices
Constraint violation: len([0]) = 1 < minCount=2
```

### Environment Expectation
The environment expected something like:
- `[0, 1]` or `[0, 2]` or `[1, 2]` (any combination of 2 distinct indices from {0, 1, 2})

---

## Part 2: Proof from Official SDK

### Source 1: Official cabt.py (Environment Handler)

**File**: `kaggle_environments/envs/cabt/cabt.py`

**Key Function**: `interpreter()` (lines 52-125 in SDK cabt.py)

```python
def interpreter(state, env):
    # ... [game start phase] ...
    else:
        error = False
        select_player = Battle.obs["current"]["yourIndex"]
        if state[select_player].status == "TIMEOUT" or state[select_player].status == "ERROR":
            error = True
        else:
            try:
                battle_select(state[select_player].action)  # <-- ACTION VALIDATION HERE
            except:
                state[select_player].status = "INVALID"  # <-- SET TO INVALID ON ERROR
                error = True

        if error:
            state[select_player].reward = -1
            state[1 - select_player].status = "DONE"
            state[1 - select_player].reward = 1
            finish(state, env)
            return state
```

**Key Point**: When `battle_select()` throws an exception (line 65-66), the environment catches it and sets `status = "INVALID"`.

### Source 2: Official game.py (Validation Dispatch)

**File**: `kaggle_environments/envs/cabt/cg/game.py`

**Key Function**: `battle_select()` (lines 39-48)

```python
def battle_select(select_list: list[int]) -> dict:
    """Select option.

    Args:
        select_list:

    Returns:
        dict: Next observation.
    """
    if not isinstance(select_list, list) or not all(isinstance(i, int) for i in select_list):
        raise ValueError("select_list is not list[int]")
    arg = (ctypes.c_int * len(select_list))(*select_list)
    err = lib.Select(Battle.battle_ptr, arg, len(select_list))  # <-- CALL TO C++ VALIDATION
    if err != 0:
        if err == 30:
            raise ValueError("battle_ptr broken.")
        else:
            raise IndexError()  # <-- RAISES IndexError ON VALIDATION FAILURE
    return _get_battle_data()
```

**Key Point**: 
- Line 43: Validates that `select_list` is a `list[int]`
- Line 44-47: Converts Python list to C++ array and calls `lib.Select()`
- Line 48-52: If C++ validation fails (`err != 0`), raises `IndexError()` 
- This exception is caught by `interpreter()` which sets status to "INVALID"

### Source 3: Official Environment Specification

**File**: `docs/environment.md` (Lines 536-554)

```markdown
### `minCount`, `maxCount`

- What they represent: lower and upper bounds on how many option indices must be returned.
- Why they exist: some prompts are single-select, some are multi-select, some are optional.
- When they change: per selection prompt.
- Example values:
  - `1/1` for exactly one choice,
  - `0/1` for optional single choice,
  - `1/3` for choose up to three but at least one.

Important note:

- The agent returns a **list of option indices**, and its length must satisfy these bounds.
```

**Key Point**: The official specification explicitly states that the agent must return a **list** whose length satisfies `minCount <= len(returned_list) <= maxCount`.

---

## Part 3: Current ActionFactory Assumption

### Source: Our Implementation

**File**: `src/poketcg/actions/factory.py`

**Method**: `from_selection()` (lines 49-57)

```python
def from_selection(self, selection: SelectPrompt, *, state: GameState | None = None) -> tuple[BaseAction, ...]:
    """Build typed actions from a parsed selection prompt."""

    attack_metadata_queue = self._attack_metadata_queue(selection, state)
    actions: list[BaseAction] = []
    for option_index, option in enumerate(selection.options):
        attack_metadata = attack_metadata_queue.pop(0) if option.option_type is OptionType.ATTACK and attack_metadata_queue else None
        actions.append(self._build_action(option_index, selection, option, state=state, attack_metadata=attack_metadata))
    return tuple(actions)
```

**Current Assumption**: 
- Line 55-56: For each option, create ONE action with `action_index = option_index`
- The factory creates N actions for N options
- Each action corresponds to selecting exactly that one option (single-selection)
- When the agent returns an integer `action_index`, it selects one option
- The wrapper then sends `[action_index]` to the environment as a list with 1 element

**Proof Code Path**:
1. `BaselineAgent.act()` receives observation with `minCount=2, maxCount=2`
2. Calls `action_factory.from_observation()` → `from_selection()`
3. `from_selection()` creates 3 actions (one per option), each for single selection
4. Agent chooses action at index 0
5. Agent returns the integer `0` (single option selected)
6. Environment wrapper sends `[0]` to `battle_select()`
7. C++ validates: `len([0]) = 1 < minCount = 2` → **VALIDATION FAILS**
8. `lib.Select()` returns error code → `raise IndexError()` in game.py
9. `interpreter()` catches exception → `status = "INVALID"`

---

## Part 4: Why This Is A Root Cause

### The Three-Part Failure

**1. Specification Gap**: 
- Official docs explicitly require respecting `minCount` and `maxCount`
- Our ActionFactory ignores these constraints
- It only creates single-select actions, never multi-select combinations

**2. Proof from SDK**:
- `minCount=2, maxCount=2` means "return exactly 2 indices"
- Game.py expects a list where `len(returned_list) >= minCount and len(returned_list) <= maxCount`
- When `len([0]) = 1 < minCount = 2`, SDK raises IndexError
- Environment catches this and marks player as INVALID

**3. Current Implementation Limitation**:
- ActionFactory creates one action per option
- Agent returns single integer per action selection
- This works for `minCount=1, maxCount=1` contexts (all our current tests pass)
- Fails catastrophically for `minCount > 1` contexts (like prize selection)

---

## Part 5: Minimal Fix Required

### Current Flow:
```
SelectPrompt(minCount=2, maxCount=2, options=[0, 1, 2])
  → from_selection() creates 3 single-select actions
  → agent picks action 0
  → returns [0]
  → environment.battle_select([0]) FAILS
```

### Required Fix:

The ActionFactory needs to:

**Option A: Create Multi-Select Actions (if minCount/maxCount != 1/1)**
```python
def from_selection(self, selection: SelectPrompt, ...) -> tuple[BaseAction, ...]:
    if selection.minCount > 1 or selection.maxCount > 1:
        # Generate combination actions: [[0,1], [0,2], [1,2], ...]
        # Agent picks one combination
        # Wrapper sends that list directly
    else:
        # Current single-selection logic
```

**Option B: Use a Different Return Format**
```python
# Instead of agent returning integer,
# Return list[int] when minCount/maxCount != 1/1
# Wrapper format: [action_index_0, action_index_1, ...]
```

**Option C: Extend BaseAction (Recommended for Type Safety)**
```python
# Create new action types:
class SingleSelectAction(BaseAction):
    action_index: int  # Selects one option

class MultiSelectAction(BaseAction):
    action_indices: list[int]  # Selects multiple options
    
# Agent returns list[int] when handling MultiSelectAction
```

### Size of Change:

Estimated modifications:
1. **ActionFactory.from_selection()**: +20-30 lines to detect `minCount != 1 or maxCount != 1`
2. **BaselineAgent**: +5-10 lines to handle multi-select context detection
3. **New multi-select action classes**: ~20 lines
4. **Tests**: +5-10 test cases for multi-select contexts

**Total**: ~60-80 lines of focused changes, no architecture redesign needed.

---

## Verification Checklist

✅ **Specification Proof**: Official docs (environment.md lines 536-554) explicitly require `minCount ≤ len(list) ≤ maxCount`

✅ **SDK Code Path**: 
- game.py `battle_select()` validates list length
- cabt.py `interpreter()` catches errors and marks INVALID

✅ **Game 2 Evidence**: 
- Returned `[0]` (length 1)
- Expected minCount=2, maxCount=2
- Environment rejected

✅ **Current Implementation Gap**: 
- ActionFactory assumes single-selection everywhere
- Does not generate multi-select combinations
- Does not respect minCount/maxCount constraints

✅ **Fix Scope**: Small, focused change to ActionFactory, no architecture impact

---

## Conclusion

The INVALID status in Game 2 is caused by a **multi-selection constraint violation** that the ActionFactory doesn't currently handle. The SDK code explicitly validates action list lengths against `minCount` and `maxCount`, and rejects actions that don't meet these constraints.

**Recommendation**: Implement multi-select action generation in ActionFactory. Do NOT implement yet—this analysis confirms the root cause is real and fixable.
