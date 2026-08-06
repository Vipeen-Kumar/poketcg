# Complete Pipeline Walkthrough: Multi-Selection Example

**Scenario**: TO_HAND selection with 3 prize card options, minCount=2, maxCount=2

---

## STAGE 1: OBSERVATION (INPUT)

```python
observation = Observation(
    state=GameState(...),
    logs=[...],
    selection=SelectPrompt(
        selection_type=SelectType.CARD,
        context=SelectContext.TO_HAND,
        min_count=2,           # ← MUST select exactly 2
        max_count=2,
        options=(
            OptionReference(type=3, area=6, index=0, playerIndex=0, ...),  # Prize 0
            OptionReference(type=3, area=6, index=1, playerIndex=0, ...),  # Prize 1
            OptionReference(type=3, area=6, index=2, playerIndex=0, ...),  # Prize 2
        ),
        effect_context=EffectContext(...),
    ),
    ...
)
```

---

## STAGE 2: ACTION FACTORY (CURRENT BEHAVIOR)

### What ActionFactory Currently Does

```python
# Current code (single-selection only)
def from_selection(self, selection: SelectPrompt, ...):
    for option_index, option in enumerate(selection.options):
        actions.append(self._build_action(option_index, selection, option, ...))
    return (
        CardChoiceAction(selected_indices=(0,), option=options[0], ...),
        CardChoiceAction(selected_indices=(1,), option=options[1], ...),
        CardChoiceAction(selected_indices=(2,), option=options[2], ...),
    )
```

**Current Result: 3 actions created**
- Action 0: `CardChoiceAction(selected_indices=(0,))`
- Action 1: `CardChoiceAction(selected_indices=(1,))`
- Action 2: `CardChoiceAction(selected_indices=(2,))`

---

## STAGE 2B: ACTION FACTORY (PROPOSED BEHAVIOR)

### What ActionFactory Would Create After Refactor

```python
# Proposed: Check minCount
def from_selection(self, selection: SelectPrompt, ...):
    if selection.min_count <= 1:
        # Single-select: current behavior (unchanged)
        for option_index, option in enumerate(selection.options):
            actions.append(self._build_action(option_index, selection, option, ...))
    else:
        # Multi-select: generate combinations
        from itertools import combinations
        option_indices = range(len(selection.options))
        for combo in combinations(option_indices, selection.min_count):
            # Create ONE action per combination
            actions.append(self._build_combination_action(combo, selection, ...))
    return tuple(actions)
```

**Proposed Result: 3 combination actions created** (C(3,2) = 3)
- Action 0: `CardChoiceAction(selected_indices=(0, 1))`
- Action 1: `CardChoiceAction(selected_indices=(0, 2))`
- Action 2: `CardChoiceAction(selected_indices=(1, 2))`

**Exact Objects**:
```python
Action0 = CardChoiceAction(
    selected_indices=(0, 1),        # ← MULTI-INDEX
    kind=ActionKind.CARD_CHOICE,
    option=options[0],              # ← Which option to use for metadata?
    selection_context=SelectContext.TO_HAND,
    selection_type=SelectType.CARD,
    chosen_card=???                 # ← Question 1 below
    chosen_index=???                # ← Question 1 below
    metadata={...},
)

Action1 = CardChoiceAction(
    selected_indices=(0, 2),
    kind=ActionKind.CARD_CHOICE,
    option=options[0],
    ...
)

Action2 = CardChoiceAction(
    selected_indices=(1, 2),
    kind=ActionKind.CARD_CHOICE,
    option=options[1],
    ...
)
```

---

## STAGE 3: DECISION CONTEXT

```python
context = DecisionContext(
    analyzer=GameAnalyzer(observation),
    legal_actions=(
        CardChoiceAction(selected_indices=(0, 1)),
        CardChoiceAction(selected_indices=(0, 2)),
        CardChoiceAction(selected_indices=(1, 2)),
    ),
    config=DecisionEngineConfig(...),
)
```

**Key point**: DecisionEngine receives 3 actions to evaluate.

---

## STAGE 4: DECISION ENGINE (UNCHANGED)

### DecisionEngine.decide() executes exactly as before:

```python
for rule in working_registry.ordered_rules():
    if not rule.applies(context):
        # Skip this rule
        continue
    else:
        result = rule.evaluate(context)  # Each rule evaluates ONE action
        if result.passed:
            return self._finalize_outcome(..., selected_result=result, ...)

# If no rule passes, use fallback
fallback_result = fallback_rule.evaluate(context)
return self._finalize_outcome(..., selected_result=fallback_result, ...)
```

**No changes needed to DecisionEngine. It still:**
1. Iterates through rules
2. Each rule evaluates actions
3. First rule to pass wins
4. Returns ONE selected action

---

## STAGE 5A: RULE EVALUATION (EXAMPLE: FALLBACK RULE)

### FallbackRule.evaluate() - DOES THIS STILL WORK?

```python
class FallbackRule(BaseRule):
    def evaluate(self, context: DecisionContext) -> RuleResult:
        if not context.legal_actions:
            raise EmptyLegalActionError("...")
        selected = context.legal_actions[0]  # ← Pick first action
        return self._result(
            passed=True,
            action=selected,
            reason="Fallback: chose first legal action.",
        )
```

**For combination actions**:
- `selected = context.legal_actions[0]` → `CardChoiceAction(selected_indices=(0, 1))`
- Returns that action unchanged
- **Works perfectly** ✓

---

## STAGE 5B: RULE EVALUATION (EXAMPLE: KNOCKOUT RULE)

### KnockoutRule.evaluate() - DOES THIS STILL WORK?

```python
class KnockoutRule(BaseRule):
    def evaluate(self, context: DecisionContext) -> RuleResult:
        actions = tuple(
            action for action in context.analyzer.attack_actions()
            if isinstance(action, AttackAction)
        )
        lethal_actions = tuple(...)
        selected = min(
            lethal_actions,
            key=lambda action: (
                attack_overkill(action, opponent_hp) or 9999,
                -attack_priority_score(action, opponent_hp)[1],
                -attack_priority_score(action, opponent_hp)[3],
                action.action_index,  # ← TIEBREAKER
            ),
        )
        return self._result(passed=True, action=selected, ...)
```

**Key question**: What is `action.action_index` for a combination action?

Currently: `@property action_index: int` returns `selected_indices[0]`

For `CardChoiceAction(selected_indices=(0, 1))`:
- `action.action_index` = 0 (first selected index)

**Does this work?**
- Rules use it only for tiebreaking when scores are equal
- For combinations, `selected_indices[0]` is still a valid first index
- Tiebreaker is deterministic (same score → pick first)
- **Works, but semantically odd** ⚠️

---

## STAGE 6: BASELINE AGENT (ACTION VALIDATION)

### BaselineAgent._validate_action_legality() - CRITICAL CHECK

The validation code:
```python
def _validate_action_legality(self, selected_action: BaseAction, artifacts):
    action_index = selected_action.action_index  # For combo: returns first index
    
    if action_index < 0 or action_index >= len(artifacts.context.legal_actions):
        # Bounds check
        raise RuntimeError(...)
    
    legal_action_at_index = artifacts.context.legal_actions[action_index]
    
    if selected_action is not legal_action_at_index:
        # Identity check
        raise RuntimeError(...)
```

**This is a HIDDEN ASSUMPTION!**

### What's the assumption?

The validation assumes:
- `action_index` uniquely identifies the action in `legal_actions`
- `legal_actions[action_index]` returns that action

**For single-select**:
- `legal_actions = [Action(0), Action(1), Action(2)]`
- `action_index = 0`
- `legal_actions[0]` = `Action(0)` ✓ Works

**For multi-select with combinations**:
- `legal_actions = [Action(0,1), Action(0,2), Action(1,2)]`
- Selected action: `Action(0,1)`
- `action_index = 0` (first selected index)
- `legal_actions[0]` = `Action(0,1)` ✓ Works IF selected is at index 0

**BUT WHAT IF**:
- Selected action: `Action(1,2)` (the third combination)
- `action_index = 1` (first selected index)
- `legal_actions[1]` = `Action(0,2)` ✗ WRONG ACTION!

### THIS IS THE CRITICAL BUG

**The validation assumes `action_index` maps to `legal_actions` array position, but for multi-select it doesn't.**

For combinations, we need a different mechanism to validate the action is in the legal set.

---

## STAGE 7: SELECTION RESOLVER (SERIALIZATION)

### SelectionResolver.resolve() - SHOULD WORK

```python
def resolve(self, action: BaseAction, selection: SelectPrompt) -> tuple[int, ...]:
    return action.selected_indices
```

For `Action(0, 1)`:
- Returns `(0, 1)` ✓

For `Action(1, 2)`:
- Returns `(1, 2)` ✓

**This works perfectly** ✓

---

## STAGE 8: SDK RESPONSE

```python
return ActionSelection(selected_option_indices=(0, 1))
```

SDK receives: `[0, 1]` ✓

Validation: `minCount=2 <= len([0,1])=2 <= maxCount=2` ✓

**VALID** ✓

---

## SUMMARY TABLE

| Component | Current Behavior | After Refactor | Works? | Notes |
|-----------|---|---|---|---|
| ActionFactory | 1 action per option | Combinations for multi-select | ✓ | Straightforward |
| DecisionEngine | Evaluate N actions | Evaluate N actions (combinations) | ✓ | Unchanged logic |
| Rules | Score actions | Score actions (same logic) | ✓ | Domain logic unchanged |
| action_index property | Returns selected_indices[0] | Same | ⚠️ | Semantically odd but works for tiebreaking |
| Validation | Uses action_index for lookup | BREAKS | ✗ | **CRITICAL ISSUE** |
| ReplayLogger | Uses action_index in description | Same | ⚠️ | Will show first index, misleading but works |
| SelectionResolver | Returns selected_indices[0] | Returns all selected_indices | ✓ | Perfect |
| SDK | Receives [0] | Receives [0, 1] | ✓ | Fixed! |

---

## ANSWERS TO YOUR 6 QUESTIONS

### 1. Does every BaseAction already contain enough metadata to represent a combination action?

**Partial YES, but with a design question:**

`BaseAction` contains:
- ✓ `selected_indices: tuple[int, ...]` (supports multi-indices)
- ✓ `option: OptionReference` (metadata)
- ✓ `selection_context`, `selection_type` (context)

**But there's an issue**: For `Action(0, 1)`, which single option should we store?
- Store options[0]? (first selected)
- Store a special "multi" marker?
- Create new action type?

**Current design unclear for multi-select actions.**

---

### 2. Does any rule assume selected_indices has length 1?

**NO** - Rules never inspect `selected_indices` directly.

All 17 rules only inspect:
- `action.kind` (type)
- `action.card` (if exists)
- `action.target_pokemon` (if exists)
- `action.action_index` (tiebreaker only)

✓ Rules work unchanged

---

### 3. Does any validation logic assume a single selected index?

**YES - CRITICAL ISSUE FOUND** ✗

`BaselineAgent._validate_action_legality()`:
```python
action_index = selected_action.action_index  # ← Returns first index only

legal_action_at_index = artifacts.context.legal_actions[action_index]
if selected_action is not legal_action_at_index:
    raise RuntimeError(...)
```

**For combinations, this breaks**:
- `Action(1, 2)` has `action_index = 1`
- `legal_actions[1]` might be `Action(0, 2)` (different action!)
- False negative validation failure

**This needs fixing before implementation.**

---

### 4. Does ReplayLogger assume only one selected index?

**NO direct assumption, but misleading output:**

```python
def _action_description(self, action):
    return f"Attack #{action.action_index}: {attack.name}"
    # For Action(0, 1) returns: "Attack #0: ..."
    # Should show: "Attack #[0, 1]: ..."
```

Works technically, but user-facing description is wrong.

---

### 5. Does ActionValidation assume only one selected index?

**YES - SAME ISSUE AS #3** ✗

The `_validate_action_legality()` method is broken for combinations.

---

### 6. Does serialization already support tuple[int,...] without changes?

**YES** ✓

```python
class ActionSelection:
    selected_option_indices: tuple[int, ...]  # Already supports this!
```

SelectionResolver and SDK already handle multi-indices correctly.

---

## CRITICAL BLOCKING ISSUES FOUND

### Issue 1: Action Validation (BLOCKS IMPLEMENTATION)

**Problem**: `_validate_action_legality()` uses `action_index` to look up in `legal_actions`, but for combinations, the first index might not be the action's position in the array.

**Current code**:
```python
action_index = selected_action.action_index  # ← First selected index
legal_action_at_index = artifacts.context.legal_actions[action_index]
if selected_action is not legal_action_at_index:
    raise RuntimeError(...)
```

**Example failure**:
- `legal_actions = [Action(0,1), Action(0,2), Action(1,2)]`
- Selected: `Action(1,2)` at array position 2
- `action_index` = 1 (first selected index)
- Looks up `legal_actions[1]` = `Action(0,2)` ✗ Wrong action!

**Solution needed**: Validate by object identity, not array position.

---

### Issue 2: ReplayLogger Description (MINOR)

**Problem**: Descriptions show only first index.

**Current**: `"Card Choice #0: Prize Card"`  
**Should be**: `"Card Choice #[0, 1]: Prize Cards"`

**Solution**: Update `_action_description()` to show full `selected_indices`.

---

### Issue 3: Action Metadata (DESIGN QUESTION)

**Problem**: For `Action(0, 1)`, which option object should we store?

**Options**:
- Store only `option` for first selected (current approach)
- Store list of options (would require BaseAction changes)
- Store None and reconstruct from indices (less complete)

**Current**: Unclear, needs design decision

---

## CONCLUSION

**Implementation is BLOCKED until these issues are resolved:**

1. **Fix action validation** - Cannot use array position lookup for combinations
2. **Decide option storage** - How to represent multi-option metadata
3. **Update ReplayLogger** - Show all indices, not just first

**These are real issues, not theoretical concerns.** The validation bug would cause runtime failures for any multi-select scenario.

