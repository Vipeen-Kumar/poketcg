# Architectural Comparison: CardChoiceAction vs CardCombinationAction

**Date**: August 6, 2026  
**Question**: Should multi-selection use extended single-select actions or dedicated action types?

---

## DOMAIN CONCEPT ANALYSIS

### What Is a Single Card Selection?
- Domain: "Player chooses one card from available options"
- Action: `CardChoiceAction(selected_index=0)`
- Metadata: Which card was chosen, from where
- Validation: Is the chosen card legal?
- Serialization: One index to SDK

### What Is a Card Combination Selection?
- Domain: "Player chooses a SET of cards from available options under constraints"
- Concept: Multi-item selection is fundamentally different
- Action: Should represent a COMBINATION, not just multiple indices
- Metadata: Which cards in the combination, constraints satisfied?
- Validation: All cards legal? Constraints satisfied (minCount, maxCount)?
- Serialization: Multiple indices to SDK

**Key insight**: These are different semantic concepts, not just different cardinalities.

---

## OPTION A: Extend CardChoiceAction

### Structure
```python
@dataclass(slots=True, kw_only=True)
class CardChoiceAction(BaseAction):
    selected_indices: tuple[int, ...]     # (0,) or (0, 1) or (0, 2)
    chosen_card: Card | None = None       # First card? All cards?
    chosen_zone: Zone | None = None       # First zone?
    chosen_index: int | None = None       # First index?
    chosen_owner: PlayerSide | None = None
    chosen_number: int | None = None
    chosen_energy_count: int | None = None
    chosen_status_condition: StatusCondition | None = None
```

### Analysis

#### Validation
```python
# Ambiguous: Which fields represent which indices?
action_index = selected_action.action_index  # First index? Always?

# For (0, 1):
# - chosen_card = card[0]? Both cards??
# - chosen_index = 0? Both 0 and 1?
# - Can't validate all selected indices easily

# Validation code must handle both cases:
if len(action.selected_indices) == 1:
    # Single-select validation
    legal_action = legal_actions[action.action_index]
else:
    # Multi-select validation: how to map (0,1) to array position?
    # No clear answer
```

**Issues**:
- ✗ Ambiguous field semantics (which field for which index?)
- ✗ Validation logic must branch on cardinality
- ✗ Array position lookup breaks for combinations

#### Replay Logging
```python
def _action_description(self, action):
    # For (0,1): show card[0]? Both?
    return f"Card Choice #{action.action_index}: {action.chosen_card.name}"
    # Output: "Card Choice #0: Prize 1"
    # But action is (0, 1), not just 0!
    # Misleading for users reviewing logs
```

**Issues**:
- ✗ Description ambiguous (which card to show?)
- ✗ User-facing output incomplete/misleading
- ✗ "Card Choice #0" doesn't indicate it's a combination

#### Rule Compatibility
```python
# Rules that check action.chosen_card:
if action.chosen_card.is_ex:
    # Assume single card
    score += 50

# For combination action (0, 1):
# Does rule check only first card?
# What if second card is EX?
```

**Issues**:
- ⚠️ Rules see only `chosen_card[0]`
- ⚠️ Multi-select semantics hidden from rules
- ⚠️ Rules can't reason about full combination

#### Serialization
```python
# SelectionResolver
return action.selected_indices

# For (0, 1): returns (0, 1) ✓
# Works fine, but no validation
```

**Status**: ✓ Works (but without context)

#### Future Discard/Select Contexts
```python
# If next context is:
# - DISCARD with minCount=2 (discard 2 cards)
# - SELECT_BENCH with minCount=2 (select 2 from bench)

# Same ambiguity applies
# Is CardChoiceAction still appropriate for DISCARD combinations?
# What about a DISCARD combination?
```

**Issues**:
- ✗ No semantic boundary (every multi-select reuses CardChoiceAction)
- ✗ Semantics of "combine N items" lost across contexts
- ✗ No clear pattern for future multi-select contexts

#### Maintainability
```python
# After 6 months: Is (selected_indices=(0,1)) a bug or intentional?
# After adding DISCARD, SWITCH_ENERGY: How do we know which fields are valid?
# After adding new context with minCount=3: Extend again?

# Code reads: "A card choice action with multiple indices"
# Meaning unclear: Is this a valid state? A bug? An edge case?
```

**Issues**:
- ✗ Semantics implicit (implicit multi-select)
- ✗ No type safety (any action can have multi-indices)
- ✗ Hard to add constraints (what makes a valid combination?)
- ✗ Scaling: Each new multi-select context reuses same type

---

## OPTION B: Dedicated CardCombinationAction

### Structure
```python
@dataclass(slots=True, kw_only=True)
class CardCombinationAction(BaseAction):
    """Represents a multi-card selection (minCount > 1)."""
    selected_indices: tuple[int, ...]      # (0, 1) or (0, 2) or (1, 2)
    selected_options: tuple[OptionReference, ...]  # Explicit options
    # Inherits from BaseAction:
    # - kind: ActionKind (already includes CARD_COMBINATION)
    # - selection_context: SelectContext
    # - selection_type: SelectType
```

### Analysis

#### Validation
```python
# Clear semantics: This action represents a SET of options
action.selected_options = (option[0], option[1])

# Validation:
# 1. All options legal? Check each in selection.options
for selected_opt in action.selected_options:
    if selected_opt not in selection.options:
        raise ValueError("Selected option not in legal options")

# 2. Constraints satisfied?
if len(action.selected_options) < selection.min_count:
    raise ValueError(f"Need {selection.min_count} options")
if len(action.selected_options) > selection.max_count:
    raise ValueError(f"Max {selection.max_count} options")

# 3. No array position lookup needed—explicit options
# BaselineAgent validation:
if action.selected_indices not in legal_combinations:
    # Can validate without array lookup
    raise ValueError("Invalid combination")
```

**Benefits**:
- ✓ Unambiguous semantics (explicit options)
- ✓ Validation logic clear (constraints on set size)
- ✓ No array position lookup needed
- ✓ Type-safe (dedicated action type)

#### Replay Logging
```python
def _action_description(self, action):
    if isinstance(action, CardCombinationAction):
        cards = [opt.card.name for opt in action.selected_options]
        return f"Card Combination: {', '.join(cards)}"
        # Output: "Card Combination: Prize 1, Prize 2"
        # Clear and complete!
    elif isinstance(action, CardChoiceAction):
        return f"Card Choice: {action.chosen_card.name}"
```

**Benefits**:
- ✓ Clear, unambiguous output (shows all cards)
- ✓ User-facing description is complete
- ✓ Type distinguishes single vs multi
- ✓ Logs explicitly show combination semantics

#### Rule Compatibility
```python
# Rules never inspect CardCombinationAction details
# They just evaluate which combination is best

# For KnockoutRule:
lethal_combos = [
    action for action in actions
    if isinstance(action, CardCombinationAction)
    and all(combo_satisfies_lethal(opt) for opt in action.selected_options)
]

# Rules work unchanged—they don't care about internal structure
# Type tells them: "This is a combination, not a single choice"
```

**Benefits**:
- ✓ Rules still work unchanged (don't inspect details)
- ✓ Type system documents intent
- ✓ Can add rule-specific logic if needed (type guards)
- ✓ Clearer code intent: combination vs single

#### Serialization
```python
# SelectionResolver
if isinstance(action, CardCombinationAction):
    return action.selected_indices  # (0, 1)
elif isinstance(action, CardChoiceAction):
    return (action.action_index,)   # (0,)

# Or simpler: Both inherit from BaseAction
return action.selected_indices  # Works for both!
```

**Benefits**:
- ✓ Type system documents intent
- ✓ Same serialization logic (selected_indices)
- ✓ Clear boundary between types

#### Future Discard/Select Contexts
```python
# When DISCARD with minCount=2 arrives:
class DiscardCombinationAction(BaseAction):
    """Represents a multi-card discard."""
    selected_indices: tuple[int, ...]
    selected_options: tuple[OptionReference, ...]

# When SELECT_ENERGY with minCount=2 arrives:
class EnergyCombinationAction(BaseAction):
    """Represents a multi-energy selection."""
    selected_indices: tuple[int, ...]
    selected_options: tuple[OptionReference, ...]

# Pattern emerges: Combination actions for multi-select
# ActionFactory.from_selection():
if selection.min_count <= 1:
    # Single-select actions (existing)
else:
    # Combination actions (new pattern)
```

**Benefits**:
- ✓ Clear pattern for all multi-select contexts
- ✓ Type hierarchy documents intent
- ✓ Each context has its own action type
- ✓ Future developers see: "Ah, combinations get their own types"
- ✓ Scalable architecture for new contexts

#### Maintainability
```python
# Code reads: "A card combination action"
# Meaning clear: This is a multi-card selection
# Intent explicit: Type name documents purpose
# Constraints: (min_count, max_count) are explicit
# Validation: Set-based, not ambiguous

# After 6 months:
if isinstance(action, CardCombinationAction):
    # I know exactly what this is
    # I know it has multiple options
    # I know constraints apply

# After adding DISCARD:
# Same pattern: DiscardCombinationAction
# Developers know: Multi-select gets its own type

# Adding minCount=3:
# CardCombinationAction still works
# No changes needed—tuple[int,...] handles any size
```

**Benefits**:
- ✓ Semantics explicit (type name)
- ✓ Constraints documented (ActionKind enum)
- ✓ Type-safe (compiler/type checker knows this is multi-select)
- ✓ Maintainable (clear intent even after months)
- ✓ Scalable (pattern clear for new contexts)

---

## COMPARISON MATRIX

| Aspect | Option A (Extend) | Option B (Dedicated) |
|--------|---|---|
| **Validation** | Ambiguous fields, branching logic | Clear set-based validation |
| **Array lookup bug** | ✗ Still broken | ✓ No lookup needed |
| **Replay logging** | ✗ Incomplete (only first card) | ✓ Complete (all cards) |
| **Rule compatibility** | ✓ Works unchanged | ✓ Works unchanged |
| **Rule visibility** | ✗ Hidden semantics | ✓ Explicit via isinstance |
| **Serialization** | ✓ Works | ✓ Works |
| **Code intent** | ✗ Implicit (magic tuple) | ✓ Explicit (type name) |
| **Type safety** | ✗ Any action can be multi | ✓ Dedicated type |
| **Future scalability** | ✗ Reuses same type | ✓ Clear pattern for new types |
| **Maintainability** | ✗ Semantics unclear | ✓ Intent explicit |
| **Complexity** | Lower (reuse existing) | Higher (new type) |
| **Correctness** | ✗ Bugs remain | ✓ Cleaner design |

---

## ARCHITECTURAL BENEFITS OF OPTION B

### 1. Type-Driven Design
```python
# For single-select: CardChoiceAction
# For multi-select: CardCombinationAction
# Compiler/IDE knows the difference

# This is fundamentally better than:
# CardChoiceAction with variable-length tuple
```

### 2. Semantic Clarity
```python
# Option A: "What does selected_indices=(0,1) mean?"
# Is this a bug? Intentional? Edge case?

# Option B: "It's a CardCombinationAction"
# Instantly clear: Multi-card selection
```

### 3. Validation Correctness
```python
# Option A validation: Must handle array position lookup (broken for combos)
# Option B validation: Set-based (always correct)
```

### 4. Scalability Pattern
```python
# Option A: Each new multi-select context reuses CardChoiceAction
# Problem: No way to distinguish different combination contexts

# Option B: Each context gets dedicated type
class CardCombinationAction(BaseAction): ...
class DiscardCombinationAction(BaseAction): ...
class EnergyCombinationAction(BaseAction): ...
# Pattern is clear and scalable
```

### 5. Future-Proof Design
```python
# Option A: Might need to add flags/fields to distinguish contexts
# Problem: Grows complex

# Option B: Already separated by type
# Clean boundary: One action type per semantic concept
```

---

## IMPLEMENTATION IMPACT

### Additional Work for Option B
- Create new action class: ~20 lines
- Update ActionFactory: +5 lines (isinstance check)
- Update validation: No special handling needed
- Update replay logger: +5 lines (isinstance check)

**Total additional code**: ~30 lines

### Payoff
- Solves validation bug (array lookup)
- Clearer semantics (type name documents intent)
- Scalable (pattern for future multi-select)
- Maintainable (explicit over implicit)
- Type-safe (compiler can help)

---

## RECOMMENDATION

**Option B (Dedicated CardCombinationAction) is architecturally superior.**

### Reasoning

1. **Correctness**: Solves validation bug without workarounds
2. **Clarity**: Type system documents multi-select semantics
3. **Scalability**: Clear pattern for DISCARD, ENERGY, and future contexts
4. **Maintainability**: Intent explicit in code (not implicit in tuple length)
5. **Type Safety**: Compiler/IDE can help catch errors
6. **Cost**: Only ~30 additional lines for significant benefits

### Why Not Option A

Option A (extend CardChoiceAction) works technically but:
- ✗ Semantics implicit (magic tuple)
- ✗ Validation logic convoluted (array position lookup broken)
- ✗ Replay logging incomplete (only shows first card)
- ✗ No clear pattern for future multi-select contexts
- ✗ Hard to distinguish single vs multi at glance

---

## FUTURE CONTEXTS THAT WILL BENEFIT

When these contexts arrive with minCount > 1:
- DISCARD (discard 2+ cards)
- SELECT_ENERGY (select 2+ energies)
- SELECT_BENCH (select 2+ Pokemon)
- SWITCH_ENERGY (switch 2+ energies)
- DAMAGE_COUNTER (place 2+ counters)

Option B provides a **clear, scalable pattern**:
```python
class DiscardCombinationAction(BaseAction): ...
class EnergyCombinationAction(BaseAction): ...
# etc.
```

Option A requires ambiguity workarounds for each.

---

## CONCLUSION

**Dedicated CardCombinationAction is the cleaner, more maintainable, more correct architecture.**

The additional ~30 lines of code pays for itself immediately through:
- Correctness (fixes validation bug)
- Clarity (explicit semantics)
- Scalability (pattern for future contexts)

