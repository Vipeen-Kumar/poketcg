# Implementation Plan: Multi-Selection Support

## Pre-Implementation Verification: ALL COMPLETE ✅

✅ **Root Cause Identified**: ActionFactory assumes single-selection everywhere  
✅ **SDK Validation Proven**: Official code requires `len(list) >= minCount and len(list) <= maxCount`  
✅ **Multi-Selection Protocol Confirmed**: Answer A) - agent returns full list `[0, 1]` once  
✅ **SDK Examples Match**: `first_agent` and `random_agent` both return full list in single call  

---

## What Needs to Change

### Current Flow (BROKEN for minCount > 1)

```
SelectPrompt(minCount=2, maxCount=2, options=[opt0, opt1, opt2])
  ↓
ActionFactory.from_selection()
  Creates 3 actions: [SingleSelectAction(0), SingleSelectAction(1), SingleSelectAction(2)]
  Each has action_index = int
  ↓
Agent chooses action 0
  ↓
Agent returns integer: 0
  ↓
Wrapper formats: [0]
  ↓
environment.battle_select([0])
  ERROR: len([0]) = 1 < minCount = 2
  ↓
Status: INVALID ❌
```

### New Flow (CORRECT for minCount > 1)

```
SelectPrompt(minCount=2, maxCount=2, options=[opt0, opt1, opt2])
  ↓
ActionFactory.from_selection()
  Detects: minCount=2, maxCount=2
  Creates combination actions: [MultiSelectAction([0,1]), MultiSelectAction([0,2]), MultiSelectAction([1,2])]
  Each has action_indices = list[int]
  ↓
Agent chooses action 0 (which is [0, 1])
  ↓
Agent returns list: [0, 1]
  ↓
Wrapper formats: [0, 1]
  ↓
environment.battle_select([0, 1])
  SUCCESS: len([0, 1]) = 2 = minCount = 2 ✅
  ↓
Status: ACTIVE/DONE ✅
```

---

## Minimal Code Changes Required

### File 1: `src/poketcg/actions/models.py`

**Add new action class** (~10 lines):

```python
@dataclass(slots=True, kw_only=True)
class MultiSelectAction(BaseAction):
    """Action representing selection of multiple options."""
    action_indices: list[int]  # The indices to select
    min_count: int  # minCount constraint
    max_count: int  # maxCount constraint
```

### File 2: `src/poketcg/actions/factory.py`

**Modify `from_selection()` method** (~40 lines):

**Key changes**:

1. **Detect multi-selection context**:
```python
def from_selection(self, selection: SelectPrompt, *, state: GameState | None = None) -> tuple[BaseAction, ...]:
    # NEW: Check if multi-selection
    if selection.minCount == 1 and selection.maxCount == 1:
        # Current single-selection logic
        return self._build_single_select_actions(selection, state)
    else:
        # NEW: Multi-selection logic
        return self._build_multi_select_actions(selection, state)
```

2. **Build multi-select combinations**:
```python
def _build_multi_select_actions(self, selection: SelectPrompt, state: GameState | None) -> tuple[BaseAction, ...]:
    """Generate all valid combination actions for multi-select context."""
    from itertools import combinations
    
    num_options = len(selection.options)
    actions = []
    
    # Generate all combinations of size minCount to maxCount
    for size in range(selection.minCount, selection.maxCount + 1):
        for combo in combinations(range(num_options), size):
            actions.append(MultiSelectAction(
                action_index=len(actions),
                action_indices=list(combo),
                min_count=selection.minCount,
                max_count=selection.maxCount,
                option=selection.options[combo[0]],  # Placeholder
                selection_context=selection.context,
                selection_type=selection.selection_type,
                metadata={},
            ))
    
    return tuple(actions)
```

### File 3: `src/poketcg/agent/baseline.py`

**Modify action execution** (~10 lines):

```python
def act(self, observation: Observation) -> int | list[int]:
    """Return action(s) for the current observation."""
    
    # ... existing decision logic ...
    
    if isinstance(chosen_action, MultiSelectAction):
        # Multi-selection: return list of indices
        return chosen_action.action_indices
    else:
        # Single-selection: return single index
        return chosen_action.action_index
```

### File 4: `src/poketcg/runner/environment_wrapper.py` (if it exists, or in game runner)

**Modify action formatting** (~5 lines):

```python
def _format_action_for_environment(agent_action):
    """Format agent action into environment-compatible format."""
    
    if isinstance(agent_action, list):
        # Multi-selection: pass list directly
        return agent_action
    else:
        # Single-selection: wrap integer in list
        return [agent_action]
```

---

## Testing Strategy

### New Test Cases

1. **Test single-select (existing behavior preserved)**:
```python
def test_single_select_unchanged():
    selection = SelectPrompt(minCount=1, maxCount=1, ...)
    actions = factory.from_selection(selection)
    assert len(actions) == 3  # One per option
    assert all(hasattr(a, 'action_index') for a in actions)
```

2. **Test multi-select action generation**:
```python
def test_multi_select_actions():
    selection = SelectPrompt(minCount=2, maxCount=2, options=[opt0, opt1, opt2])
    actions = factory.from_selection(selection)
    # Should create C(3,2) = 3 combinations: [0,1], [0,2], [1,2]
    assert len(actions) == 3
    assert all(isinstance(a, MultiSelectAction) for a in actions)
```

3. **Test minCount=1, maxCount=2 (optional multi-select)**:
```python
def test_optional_multi_select():
    selection = SelectPrompt(minCount=1, maxCount=2, options=[opt0, opt1, opt2])
    actions = factory.from_selection(selection)
    # Should create: [0], [1], [2], [0,1], [0,2], [1,2]
    assert len(actions) == 6
```

4. **Test environment validation**:
```python
def test_environment_accepts_multi_select():
    env = make_test_env()
    # Simulate agent returning [0, 1]
    action = [0, 1]
    env.step(action)  # Should not raise
    assert env.status != "INVALID"
```

### Integration Test

```python
def test_game_with_prize_selection():
    """Test a game that exercises prize selection (minCount=2)."""
    agent = BaselineAgent()
    env = make("cabt", configuration={"decks": [deck1, deck2]})
    
    # Run game
    steps = env.run([agent, agent])
    
    # Both players should reach DONE, not INVALID
    assert steps[-1][0].status == "DONE"
    assert steps[-1][1].status == "DONE"
```

---

## Rollout Plan

### Phase 1: Implement (Minimal Risk)
- Add `MultiSelectAction` class
- Add `_build_multi_select_actions()` method
- Modify `from_selection()` to detect and route correctly
- Add return type handling in agent
- Update environment wrapper formatting

### Phase 2: Test (Comprehensive)
- Run all existing tests (should pass - single-select unchanged)
- Run new multi-select tests
- Test with sample agents (first_agent, random_agent)
- Test Game 2 reproduction

### Phase 3: Verify
- Run full test suite: `python -m unittest discover -s tests -p "test_*.py" -v`
- Run build check: `python -m compileall src tests`
- Test against problematic game seeds

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Breaking single-select | LOW | Logic branched, single-select path unchanged |
| Combination explosion | LOW | Only generate valid combinations, capped by game rules |
| Agent compatibility | LOW | Agent already handles list returns in some contexts |
| Performance | LOW | Combination generation is O(C(n,k)) where n ≤ 60 typically |

---

## Success Criteria

✅ **All 99 existing tests pass**  
✅ **New multi-select tests pass**  
✅ **Game 2 INVALID is resolved** (if re-run with multi-select support)  
✅ **Build succeeds**: `python -m compileall src tests`  
✅ **No performance regression** in game runner  

---

## Implementation Readiness: READY ✅

All verification complete. Implementation can proceed immediately upon approval.
