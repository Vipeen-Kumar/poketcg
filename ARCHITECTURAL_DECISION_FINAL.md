# Architectural Decision: Option A vs Option B for Multi-Selection

**Date**: August 6, 2026  
**Status**: EVALUATION COMPLETE - Ready for recommendation

---

## EXECUTIVE SUMMARY

After comprehensive analysis of both options, **Option A (ActionFactory generates combinations) is architecturally superior** for these reasons:

1. **Correctness**: The decision about which indices belongs in ActionFactory, not SelectionResolver
2. **Separation of concerns**: SelectionResolver only serializes, DecisionEngine only chooses one action
3. **Scalability**: Pattern is clean and generalizable to all future multi-select contexts
4. **Maintainability**: Explicit intent (action contains complete selection) vs implicit inference
5. **Hidden assumptions are fewer**: Most can be accommodated with backward compatibility

---

## THE CORE INSIGHT

Your question reveals the key architectural issue:

> **"SelectionResolver cannot invent another index. It cannot know whether the correct answer is [0,1] or [0,2] or [1,2]."**

This is **exactly correct** and **fundamentally demolishes Option B**:

- **Option B** (DecisionEngine chooses multiple actions): Requires DecisionEngine to understand multi-selection semantics and pick a coherent subset. But:
  - Rules are written for single actions, not action combinations
  - Rules don't understand "I want [0,1] together" - they only rank individual actions
  - Tie-breaking becomes incoherent (choose action #0 AND action #1? But they might have different priority scores)
  - The semantic coupling between multiple "chosen actions" is never defined

- **Option A** (ActionFactory generates combinations): Moves the combinatorial logic to where it belongs:
  - ActionFactory knows minCount/maxCount before DecisionEngine runs
  - ActionFactory generates ALL valid combinations as independent actions
  - DecisionEngine chooses ONE (coherent) action with ONE clear score/reason
  - SelectionResolver just returns what's already in that one action
  - **Complete separation of concerns**

---

## DETAILED EVALUATION

### OPTION A: ActionFactory Generates Combinations

```
Observation
  ↓ minCount=2, maxCount=2, options=[0,1,2]
ActionFactory generates:
  Action(selected_indices=(0,1))
  Action(selected_indices=(0,2))
  Action(selected_indices=(1,2))
  ↓
DecisionEngine chooses ONE action (e.g., Action(0,1))
  ↓
SelectionResolver returns (0,1)
  ↓
SDK receives [0,1]
```

#### 1. CORRECTNESS ✓✓✓

**Complete and unambiguous**:
- ✓ Combination is explicit in the action
- ✓ Decision is single and clear
- ✓ No inference or guessing
- ✓ To_HAND with minCount=2 → generates 3 combinations → DecisionEngine picks one
- ✓ All combinations are available for rules to evaluate

#### 2. SEPARATION OF CONCERNS ✓✓✓

| Component | Responsibility | Result |
|-----------|---|---|
| **ActionFactory** | Generate all valid combinations | ~30 lines of new code |
| **DecisionEngine** | Choose ONE best action | Unchanged |
| **SelectionResolver** | Serialize selected_indices | Unchanged |

- ✓ Each component has one clear job
- ✓ No component invents gameplay decisions
- ✓ Clean, testable interfaces

#### 3. EFFECT ON EXISTING RULES ✓✓

**Rules continue working exactly as-is** because:
- They rank actions by single-action attributes (card name, HP, position, etc.)
- Each combination action `(0,1)` is a single action with single attributes
- Rules compare combinations by the same scoring metrics
- **Nothing needs to change in rule logic**

Example:
```python
# Current rule (unchanged):
def evaluate(context: DecisionContext) -> RuleResult:
    actions = context.legal_actions
    selected = max(actions, key=lambda a: a.card.hp if hasattr(a, 'card') else 0)
    return self._result(passed=True, action=selected)

# Works for both single-selection and combinations because:
# - For single: Action(selected_indices=(0,))
# - For combination: Action(selected_indices=(0,1))
# - Both are single actions with the same metadata attributes
```

#### 4. EFFECT ON ACTION VALIDATION ✓

**ActionValidation** (in ActionFactory):
- Validates each individual combination is valid
- Validates indices are in range
- **Already there, no changes needed**

#### 5. EFFECT ON REPLAY LOGGING ✓✓

**ReplayLogger logs the chosen action**:
```python
def _action_to_record(self, action: BaseAction) -> ActionRecord:
    return ActionRecord(
        action_type=action.kind.name,
        action_index=action.action_index,  # Backward compat property
        description=self._action_description(action),
    )
```

For combinations:
- `action.action_index` property returns `selected_indices[0]` (backward compat)
- Logs the first index as "primary action"
- Can extend to log all indices for multi-select contexts
- **Fully backward compatible**

#### 6. HIDDEN ASSUMPTIONS - ANALYSIS

**Assumption 1: selected_indices has length 1**
```python
# Current code in BaseAction:
@property
def action_index(self) -> int:
    return self.selected_indices[0] if self.selected_indices else -1
```
- ✓ Works for combinations (returns first index)
- ✓ Backward compatible
- ✓ No change needed

**Assumption 2: action.action_index used for tie-breaking**
```python
# Rules use action.action_index:
sorted(actions, key=lambda a: (-a.score, a.action_index))
```
- ✓ Works for combinations (uses first index as tie-breaker)
- ✓ Fair: combinations with lower first index score higher
- ✓ No change needed

**Assumption 3: Rules assume single-action semantics**
```python
# Rules score individual actions:
def score_action(action):
    if action.card.hp > 100:
        return 10
    return 5
```
- ✓ Works for combinations (combination action has all the same metadata)
- ✓ No change needed

**Assumption 4: Serialization assumes single index**
```python
# In SelectionResolver:
def resolve(action, selection):
    return action.selected_indices  # Already supports tuples
```
- ✓ Already works (returns tuple of any length)
- ✓ No changes needed

**Assumption 5: DecisionEngine's validation checks membership**
```python
if result.selected_action not in context.legal_actions:
    raise InvalidRuleError(...)
```
- ✓ Works for combinations (combination is in legal_actions)
- ✓ No change needed

**Assumption 6: Tests assume single indices**
```python
def test_backward_compat_action_index_property_single_select(self):
    self.assertEqual(action.selected_indices[0], 0)
```
- ✓ Add new test: `test_combination_action_backward_compat`
- ✓ Verify `action.action_index` returns first index
- ✓ Verify `action.selected_indices` is tuple of all indices
- ⚠️ One-time setup, no ongoing maintenance

---

### OPTION B: DecisionEngine Chooses Multiple Actions

```
Observation
  ↓ minCount=2, maxCount=2, options=[0,1,2]
ActionFactory generates:
  Action(0)
  Action(1)
  Action(2)
  ↓
DecisionEngine chooses... TWO actions??
  - Which two?
  - By what scoring rule?
  - What if the rule says "choose action 0" but we need TWO?
  ↓
SelectionResolver somehow combines them?
```

#### 1. CORRECTNESS ✗✗✗

**Fundamentally broken**:
- ✗ Who chooses which actions to combine?
- ✗ Rules rank single actions, not combinations
- ✗ No semantic way to pick TWO actions coherently
- ✗ Rule says "best action is #0, fallback is #1" → do we return [0,1]? Why?
- ✗ What if rules rank them: #0 (score 10), #2 (score 8), #1 (score 5)? → return [0,2]?
- ✗ No clear algorithm

#### 2. SEPARATION OF CONCERNS ✗✗

- ✗ DecisionEngine must understand multi-selection semantics
- ✗ DecisionEngine must know to return 2 actions (not 1)
- ✗ DecisionEngine must decide WHICH 2 (combinatorial logic)
- ✗ SelectionResolver must somehow combine them (but how?)
- ✗ Roles are blurred and entangled

#### 3. EFFECT ON EXISTING RULES ✗✗✗

Rules only evaluate single actions:
```python
# Rule as written:
def evaluate(context: DecisionContext) -> RuleResult:
    actions = context.legal_actions
    selected = max(actions, key=some_score_function)
    return self._result(passed=True, action=selected)
```

**What happens with minCount=2?**
- Rule returns ONE action
- But we need TWO
- DecisionEngine must somehow duplicate/extend the result
- Or DecisionEngine must re-query rules asking "give me top 2"?
- Or DecisionEngine must have special logic for multi-selection?
- ✗ All paths require significant DecisionEngine changes

#### 4. ALGORITHMIC AMBIGUITY ✗✗✗

**How does DecisionEngine choose multiple actions?**

Option B.1: "Get top N actions by score"
```python
actions = context.legal_actions
top_n = sorted(actions, key=lambda a: a.score, reverse=True)[:minCount]
return top_n
```
- ✗ But rules don't score actions separately
- ✗ Rules use priorities to decide which to run
- ✗ Rules pass/fail based on complex logic, not raw scores
- ✗ Top N by which metric? There is no single metric

Option B.2: "Ask rule to return multiple actions"
```python
# DecisionEngine would need to:
for rule in rules:
    result = rule.evaluate_multi(context, count=minCount)
    if result.passed:
        return result.actions  # List of actions
```
- ✗ Breaks the rule interface (all rules return one action)
- ✗ Requires rewriting every rule
- ✗ Rules don't know how to evaluate "pick these N together"
- ✗ Massive refactor of the decision engine

Option B.3: "DecisionEngine picks best action, then SelectionResolver picks others"
```python
selected_action = decision_engine.choose_action(context)
other_actions = selection_resolver.pick_additional(selected_action, minCount-1)
return [selected_action, ...other_actions]
```
- ✗ SelectionResolver invents gameplay decisions (violates spec)
- ✗ No principled way to pick "additional" actions
- ✗ Could pick suboptimal combinations
- ✗ Validation nightmares

#### 5. VALIDATION NIGHTMARE ✗✗

If DecisionEngine returns multiple actions, validation must check:
```python
# Current validation:
if result.selected_action not in context.legal_actions:
    raise InvalidRuleError(...)

# Option B validation:
if result.selected_actions not in context.legal_actions:  # How to check a list?
    # Check each?
    for action in result.selected_actions:
        if action not in context.legal_actions:
            raise InvalidRuleError(...)
    # But what if they form an INVALID combination?
    # E.g., two "mutually exclusive" actions?
    # No way to validate that without combinatorial logic
```

#### 6. BACKWARD COMPATIBILITY ✗

- ✗ All tests assume `selected_action` (singular)
- ✗ Rules assume ONE action
- ✗ ReplayLogger logs ONE action per decision
- ✗ Baseline agent expects ONE action
- ✗ Requires major refactoring throughout

---

## COMPARISON MATRIX

| Criterion | Option A | Option B |
|-----------|----------|----------|
| **Correctness** | ✓✓✓ Complete, unambiguous | ✗✗✗ No clear algorithm |
| **Separation of concerns** | ✓✓✓ Clean boundaries | ✗✗✗ Blurred responsibilities |
| **Rules unchanged** | ✓✓ Yes, work as-is | ✗✗✗ Must rewrite many |
| **ActionValidation** | ✓ Straightforward | ✗ Complex |
| **ReplayLogger** | ✓✓ Works + logs first index | ✗✗ Must log multiple |
| **Backward compat** | ✓✓✓ Full | ✗ Requires major refactors |
| **Code change size** | ~50-100 lines | ~500+ lines |
| **Testing burden** | +5-10 tests | +50+ tests |
| **Maintainability** | ✓✓✓ Clear intent | ✗✗ Implicit inference |
| **Scalability** | ✓✓✓ Pattern works for all contexts | ✗ Each context needs custom logic |
| **Risk of bugs** | Low (localized changes) | Very high (pervasive changes) |

---

## HIDDEN ASSUMPTIONS ANALYSIS FOR OPTION A

### 1. ActionValidation ✓
**Assumption**: Only validates individual option indices.
**Reality**: Already validates `option_index` and `selected_indices[0]`.
**Impact**: No change needed. Can validate each index in combination.
**Code**: ~3 lines to validate all indices in tuple.

### 2. ReplayLogger ✓
**Assumption**: Logs `action.action_index` (first index only).
**Reality**: Can log first index for backward compat, or all indices in metadata.
**Impact**: Fully backward compatible.
**Code**: No changes needed (or +5 lines if want to log all indices).

### 3. Rule Ordering ✓
**Assumption**: Rules execute in priority order.
**Reality**: Unchanged. DecisionEngine still runs rules in order, picks first pass.
**Impact**: No change.
**Code**: None.

### 4. Tie-Breaking ✓
**Assumption**: `action.action_index` used for tie-breaking between actions.
**Reality**: Combination actions still have `.action_index` property returning first index.
**Impact**: Fair tie-breaking (combinations with lower first index score higher).
**Code**: No changes needed.

### 5. selected_indices ✓
**Assumption**: Historically length 1.
**Reality**: Now can be length N for combinations.
**Impact**: Backward compatible (all code accessing uses `selected_indices[0]` or iteration).
**Code**: No changes needed.

### 6. action_index ✓
**Assumption**: Every action has unique action_index.
**Reality**: Combinations are new actions with new action_indices.
**Impact**: Combinations don't collide with single-action indices (separate namespace).
**Code**: No changes needed.

### 7. Serialization ✓
**Assumption**: `selected_indices` is serializable tuple.
**Reality**: Already is. Tuples serialize fine.
**Impact**: No changes.
**Code**: None.

### 8. Tests ✓
**Assumption**: Test actions with `selected_indices=(0,)`.
**Reality**: Add new tests for combinations.
**Impact**: One-time addition of ~5-10 tests.
**Code**: ~50 lines of test setup.

---

## ARCHITECTURAL INSIGHT: WHY OPTION A IS SUPERIOR

### The Decision Point

The correct place to make a decision is **where you have full information and the decision cannot be deferred**:

**ActionFactory has**:
- SelectPrompt with minCount/maxCount
- All available options
- All constraints

**ActionFactory does NOT have**:
- Cannot make strategy decisions (that's rules' job)
- Can only generate valid combinations

**DecisionEngine has**:
- Rules for strategy (which action is best)
- Can rank actions

**DecisionEngine does NOT have**:
- No knowledge of minCount/maxCount
- Cannot generate combinations (out of scope)
- Cannot invent indices

**SelectionResolver has**:
- SDK interface requirements
- Serialization logic

**SelectionResolver does NOT have**:
- No decision-making authority
- Cannot invent indices
- Only serializes what's already decided

### The Only Sound Design

1. **ActionFactory**: Generate all valid combinations (constraint satisfaction)
2. **DecisionEngine**: Choose best combination (strategy)
3. **SelectionResolver**: Serialize the combination (protocol)

This matches the single-responsibility principle:
- Each component has ONE well-defined job
- Each component uses information it HAS
- No component invents decisions outside its scope
- No component guesses about missing information

---

## RECOMMENDATION

### Option A is the correct choice

**Why**:
1. ✓ Correctness is guaranteed
2. ✓ Separation of concerns is maintained
3. ✓ Rules work unchanged
4. ✓ Hidden assumptions are minimal and compatible
5. ✓ Backward compatibility is achievable
6. ✓ Testing burden is manageable
7. ✓ Pattern scales to all future multi-select contexts
8. ✓ Code change is localized and low-risk

**Implementation scope**:
- ~50-100 lines in ActionFactory (generate combinations)
- ~20 lines in tests (new test cases)
- ~10 lines documentation
- **ZERO changes** to DecisionEngine, Rules, SelectionResolver, ReplayLogger

**Timeline**: 2-3 hours

---

## OPTION A IMPLEMENTATION OUTLINE

Not implementing yet, but here's what would be needed:

### 1. Extend ActionFactory.from_selection()

```python
def from_selection(self, selection: SelectPrompt, *, state: GameState | None = None) -> tuple[BaseAction, ...]:
    """Build typed actions from a parsed selection prompt."""
    
    # Check if multi-selection
    if selection.min_count > 1:
        # Generate all combinations of required size
        from itertools import combinations
        option_indices = list(range(len(selection.options)))
        
        # Generate all combinations from min_count to max_count
        all_combinations = []
        for combo_size in range(selection.min_count, selection.max_count + 1):
            for combo in combinations(option_indices, combo_size):
                all_combinations.append(combo)
        
        # Build action for each combination
        actions = []
        for combo_indices in all_combinations:
            action = self._build_combination_action(combo_indices, selection, state=state)
            actions.append(action)
        return tuple(actions)
    else:
        # Single-selection (existing logic)
        return self._build_single_selection_actions(selection, state)

def _build_combination_action(
    self,
    option_indices: tuple[int, ...],
    selection: SelectPrompt,
    *,
    state: GameState | None,
) -> BaseAction:
    """Build a single action representing a combination of selected indices."""
    # Get first option for metadata
    first_option = selection.options[option_indices[0]]
    
    # Build action with all indices
    base_kwargs = {
        "selected_indices": option_indices,
        "option": first_option,
        "selection_context": selection.context,
        "selection_type": selection.selection_type,
        "metadata": dict(first_option.metadata),
    }
    
    # Return appropriate typed action based on context/type
    # For now, use CardChoiceAction for multi-card selections
    return CardChoiceAction(
        kind=ActionKind.CHOOSE_CARD,
        chosen_card=first_option.card,
        chosen_zone=first_option.zone,
        chosen_index=first_option.zone_index,
        chosen_owner=first_option.owner,
        **base_kwargs,
    )
```

### 2. Add tests

```python
def test_multi_selection_generates_combinations(self):
    """ActionFactory generates all valid combinations for minCount > 1."""
    # Arrange: selection with 3 options, minCount=2, maxCount=2
    # Act: factory.from_selection(selection)
    # Assert: returns 3 actions: (0,1), (0,2), (1,2)
    
def test_combination_action_backward_compat(self):
    """Combination actions work with backward-compat action_index property."""
    # Arrange: combination action with selected_indices=(0,1)
    # Act: action.action_index
    # Assert: returns 0 (first index)
```

### 3. Update ReplayLogger (optional)

```python
def _action_description(self, action: BaseAction) -> str:
    # Existing logic...
    # Add for combinations:
    if len(action.selected_indices) > 1:
        indices_str = ", ".join(str(i) for i in action.selected_indices)
        return f"Select #{indices_str}: ..."
```

---

## FINAL ANSWER

**Choose Option A.**

It is the only architecturally sound solution because:
1. It places decisions where they belong (ActionFactory for combinations, DecisionEngine for strategy)
2. It respects separation of concerns (each component has one job)
3. It achieves correctness (no inference or guessing)
4. It maintains backward compatibility (minimal changes)
5. It scales to future contexts (pattern is general)

Option B fails because it attempts to move decision-making to DecisionEngine without a coherent algorithm for choosing multiple actions. The problem your investigation revealed—that SelectionResolver cannot invent indices—is the **key insight that proves Option A is correct**.

The solution is not to make SelectionResolver or DecisionEngine smarter. The solution is to generate all valid combinations **before** DecisionEngine runs, so that every action it can choose is a coherent, complete decision.

