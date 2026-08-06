# Design Evaluation: Combination Actions for Multi-Selection

**Date**: August 6, 2026  
**Architecture**: Generate combination actions in ActionFactory when minCount > 1

---

## EXECUTIVE SUMMARY

**Verdict**: This architecture is **viable and architecturally sound**.

It preserves the decision engine and rules system exactly as-is. All existing rules continue working unchanged. The work is localized to ActionFactory and SelectionResolver.

---

## QUESTION 1: How Many Files Would Change?

### Files Modified

| File | Type | Change | Impact |
|------|------|--------|--------|
| `src/poketcg/actions/factory.py` | MODIFY | Add combination generation logic | Isolated to from_selection() method |
| `src/poketcg/actions/models.py` | MODIFY | Add multi-selection action type (optional) | Or reuse BaseAction with multi-indices |
| `src/poketcg/selection/registry.py` | MODIFY | Update dispatch if needed | Minimal—may stay unchanged |
| `src/poketcg/selection/generic.py` | MODIFY | Handle multi-indices | Minor enhancement |

### Files NOT Changed

✓ `src/poketcg/decision/engine.py` - DecisionEngine logic unchanged  
✓ `src/poketcg/decision/context.py` - DecisionContext unchanged  
✓ `src/poketcg/rules/*.py` (all 17 rule files) - Unchanged  
✓ `src/poketcg/agent/baseline.py` - No changes needed  
✓ `src/poketcg/domain/models.py` - Observation structure unchanged  

### Test Files

| File | Type | Change |
|------|------|--------|
| `tests/actions/test_action_factory.py` | MODIFY | Add multi-selection factory tests |
| `tests/actions/test_multi_selection_actions.py` | NEW | Test combination generation |
| `tests/selection/test_multi_resolver.py` | MODIFY/NEW | Test multi-select resolution |

**Total files modified: ~4**  
**Total files created: ~2**  
**Files affected: 6**

---

## QUESTION 2: Which Existing Rules Continue Working Unchanged?

### Answer: ALL 17 EXISTING RULES

Here's why:

**Rule Evaluation Process**:
```python
# A rule receives one action and evaluates it
for action in context.legal_actions:  # Can be combination action now
    score = evaluate(action)
    if score > best_score:
        selected_action = action
```

**Why rules don't break**:

1. **Rules evaluate single actions** → Rules receive one action at a time (whether single-index or combination-index)
2. **Rules don't examine selected_indices** → Rules examine action type and metadata, not the indices
3. **Rules use action_index property** → This is backward-compatible (can work with combinations)
4. **Rules select by domain logic** → "Best attack", "best evolution", etc.—logic is unchanged

### Example: AttackRule (unchanged)

```python
class AttackRule(BaseRule):
    def evaluate(self, context: DecisionContext) -> RuleResult:
        actions = tuple(
            action for action in context.analyzer.attack_actions() 
            if isinstance(action, AttackAction)
        )
        selected = max(actions, key=lambda action: attack_priority_score(action, opponent_hp))
        return self._result(passed=True, action=selected, ...)
```

**With combination actions**:
- Rules still see AttackAction instances (only the selected_indices field changed)
- Rules still evaluate by domain logic (damage, opponent HP, etc.)
- Rules still select best action (same scoring function)
- **Zero changes needed** ✓

### Example: FallbackRule (unchanged)

```python
class FallbackRule(BaseRule):
    def evaluate(self, context: DecisionContext) -> RuleResult:
        if not context.legal_actions:
            raise EmptyLegalActionError("...")
        return self._result(passed=True, action=context.legal_actions[0], ...)
```

**With combination actions**:
- Fallback still picks first legal action (could be a combination)
- Fallback behavior unchanged
- **Zero changes needed** ✓

### All 17 Rules Listed

✓ `AbilityRule` - Evaluates ability actions, unchanged  
✓ `AttackRule` - Evaluates attack actions, unchanged  
✓ `AttachEnergyRule` - Evaluates energy attachment, unchanged  
✓ `EndTurnRule` - Evaluates end-turn action, unchanged  
✓ `EvolutionRule` - Evaluates evolution actions, unchanged  
✓ `FallbackRule` - Returns first legal action, unchanged  
✓ `ItemRule` - Evaluates item plays, unchanged  
✓ `KnockoutRule` - Evaluates lethal attacks, unchanged  
✓ `PrizeRule` - Evaluates prize-scoring attacks, unchanged  
✓ `RetreatRule` - Evaluates retreat actions, unchanged  
✓ `StadiumRule` - Evaluates stadium plays, unchanged  
✓ `SupporterRule` - Evaluates supporter plays, unchanged  
✓ `WinningAttackRule` - Evaluates winning attacks, unchanged  
✓ (Plus base rules and strategy utilities)

---

## QUESTION 3: Estimated Combination Counts

### For minCount=2, maxCount=2 (exactly 2 selections)

| Options | Combinations | Examples |
|---------|---|---|
| 3 | **3** | (0,1), (0,2), (1,2) |
| 4 | **6** | (0,1), (0,2), (0,3), (1,2), (1,3), (2,3) |
| 5 | **10** | C(5,2) = 10 |
| 6 | **15** | C(6,2) = 15 |
| 7 | **21** | C(7,2) = 21 |
| 8 | **28** | C(8,2) = 28 |
| 9 | **36** | C(9,2) = 36 |
| 10 | **45** | C(10,2) = 45 |

### Real-World Context: Prize Selection

**TO_HAND (return to hand) with minCount=2**:
- Player typically has 3-6 prize cards remaining
- 3 prizes → 3 combinations (manageable)
- 6 prizes → 15 combinations (acceptable)

**TO_PRIZE (add to prize) with minCount=1, maxCount=3**:
- Typically 0-2 options in this context (rare)
- Unlikely to exceed 10 combinations

### Scalability Assessment

| Range | Assessment |
|-------|---|
| 0-20 combinations | ✓ Excellent (3-6 prize cards) |
| 20-100 combinations | ✓ Good (rare cases, still fast) |
| 100-1000 combinations | ⚠️ Warning (large option sets) |
| 1000+ combinations | ✗ Problem (combinatorial explosion) |

**Real PTCG game context**: Option sets rarely exceed 10 items
- Prize cards: 6 maximum
- Hand cards in a choice: typically 3-5
- Bench Pokemon: 5 maximum
- Discard pile selections: usually <10

**Conclusion**: Combination generation is **highly practical** for PTCG contexts.

---

## QUESTION 4: Does This Preserve Current Architecture Better?

### Comparison: Alternative Approaches

#### Option A: Generate Combinations in ActionFactory (PROPOSED) ✓

**How it works**:
```
Observation (minCount=2, options=[0,1,2])
  ↓
ActionFactory generates:
  - Action(selected_indices=(0,1))
  - Action(selected_indices=(0,2))
  - Action(selected_indices=(1,2))
  ↓
DecisionEngine evaluates 3 actions normally
  ↓
DecisionEngine selects one: Action(0,1)
  ↓
BaselineAgent gets one action with selected_indices=(0,1)
  ↓
SelectionResolver serializes (0,1) → [0,1] to SDK
```

**Changes required**:
- ActionFactory: +50-100 lines (combination generation)
- SelectionResolver: +20 lines (support multi-indices)
- Rules: ZERO changes

**Architecture impact**: **MINIMAL** ✓

---

#### Option B: Modify DecisionEngine to Select Multiple Actions ✗

**How it would work**:
```
DecisionEngine returns: [Action(0), Action(1)]
```

**Changes required**:
- DecisionEngine: Major refactor (~200 lines)
- RuleResult: Change selected_action to selected_actions (list)
- Rules: Update all 17 rules to return lists
- BaselineAgent: Handle multiple actions
- SelectionResolver: Unpack multiple actions

**Architecture impact**: **SEVERE** ✗

---

#### Option C: Make SelectionResolver Invent Indices ✗

**How it would work**:
```
SelectionResolver receives action=(0,), minCount=2
SelectionResolver guesses: return (0,1)
```

**Problems**:
- No principled basis for guessing (0,1) vs (0,2)
- Gameplay decisions become non-deterministic
- Violates "SelectionResolver is serialization only"

**Architecture impact**: **BROKEN** ✗

---

### Why Option A Preserves Architecture Best

| Aspect | Status |
|--------|--------|
| DecisionEngine unchanged | ✓ Yes |
| Rule system unchanged | ✓ Yes (all 17 rules) |
| BaselineAgent logic unchanged | ✓ Yes |
| GameState evaluation unchanged | ✓ Yes |
| Action types unchanged | ✓ Yes (extend existing) |
| SelectionResolver stays pure | ✓ Yes (serialization only) |
| Decision logic untouched | ✓ Yes |
| Backward compatible | ✓ Yes |

**Conclusion**: Option A is the **cleanest architectural choice**.

---

## IMPLEMENTATION SCOPE

### Changes in ActionFactory

**Current**:
```python
def from_selection(self, selection: SelectPrompt, ...):
    actions = []
    for option_index, option in enumerate(selection.options):
        actions.append(self._build_action(option_index, selection, option, ...))
    return tuple(actions)
```

**New logic**:
```python
def from_selection(self, selection: SelectPrompt, ...):
    if selection.min_count <= 1:
        # Single-select: current behavior
        actions = [self._build_action(i, ...) for i in range(len(selection.options))]
    else:
        # Multi-select: generate combinations
        from itertools import combinations
        actions = []
        for combo in combinations(range(len(selection.options)), selection.min_count):
            actions.append(self._build_combination_action(combo, selection, ...))
    return tuple(actions)
```

**Key insight**: `_build_combination_action()` creates ONE action with `selected_indices=combo`

---

## RISK ASSESSMENT

### Low Risk ✓

1. **Localized changes**: Only ActionFactory and SelectionResolver affected
2. **No rule modifications**: All 17 rules work unchanged
3. **No engine changes**: DecisionEngine logic identical
4. **Backward compatible**: Single-select (minCount=1) behavior unchanged
5. **Reversible**: Can remove combination logic if issues arise
6. **Tested easily**: Combination generation is pure function (no dependencies)

### Medium Risk (Acceptable)

1. **Combination explosion**: For large option sets (10+ items)
   - Mitigation: Real PTCG has small option sets (<10 usually)
   - Worst case: 45 combinations for 10 items → DecisionEngine still evaluates them

2. **Rule evaluation time**: More actions to evaluate
   - Mitigation: DecisionEngine already fast; 45 actions is trivial
   - Current system evaluates 30-50 actions per decision anyway

---

## DATA FLOW (PROPOSED ARCHITECTURE)

```
Selection (minCount=2, maxCount=2, 3 options)
    ↓
ActionFactory.from_selection()
    ├─ Generates: Action(0,1), Action(0,2), Action(1,2)
    ├─ Each has full metadata (card, zone, etc.)
    └─ selected_indices contains the multi-index tuple
    ↓
DecisionContext.legal_actions = [Action(0,1), Action(0,2), Action(1,2)]
    ↓
Rules evaluate each action (3 options)
    └─ Each rule picks best combo by domain logic
    ↓
DecisionEngine selects ONE: Action(0,1)
    ↓
BaselineAgent.act()
    ├─ selected_action = Action(0,1)
    ├─ selected_indices = (0,1)
    └─ Calls SelectionResolver.resolve()
    ↓
SelectionResolver.resolve(action=(0,1), minCount=2)
    └─ Returns (0,1) ✓
    ↓
BaselineAgent returns: ActionSelection([0,1])
    ↓
SDK receives: [0, 1] ✓ VALID (minCount satisfied)
```

---

## SUMMARY

| Criterion | Evaluation |
|-----------|---|
| **Files Changed** | ~6 (minimal) |
| **Rules Affected** | 0 of 17 (unchanged) |
| **Engine Changes** | None (unchanged) |
| **Combinations for 3-6 items** | 3-15 (acceptable) |
| **Architectural Purity** | High (serialization-only resolvers) |
| **Backward Compatibility** | Full ✓ |
| **Risk Level** | Low ✓ |
| **Scalability** | Good for PTCG constraints |

**Recommendation**: This architecture is **sound and implementable**.

---

## NEXT STEPS (IF APPROVED)

1. Implement combination generation in ActionFactory
2. Add combination action generation helpers
3. Update SelectionResolver to handle multi-indices
4. Add unit tests for combination generation
5. Add integration tests (100-game run)
6. Verify all 17 rules work unchanged
7. Run full test suite

