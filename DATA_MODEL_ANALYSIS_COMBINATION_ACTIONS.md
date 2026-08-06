# Data Model Analysis: Can BaseAction Represent Combination Actions?

**Investigation Date**: August 6, 2026  
**Scope**: Complete trace of BaseAction fields for combination action `Action(selected_indices=(0,1))`

---

## HYPOTHETICAL SCENARIO

```
Selection with minCount=2, maxCount=2, options:
  Option 0: Pikachu (card)
  Option 1: Charizard (card)
  Option 2: Rare Candy (card)

ActionFactory would generate combination:
  Action(selected_indices=(0, 1))
  - Pikachu AND Charizard together
```

---

## BASEACTION FIELD ANALYSIS

### 1. `selected_indices: tuple[int, ...]`

**Current value for combination action**: `(0, 1)`

**Meaning**: The indices of the selected options.

**Is it still meaningful?** ✓ YES
- For single-selection: `(0,)` means "choose option 0"
- For combination: `(0, 1)` means "choose options 0 and 1 together"
- **Fully compatible, more expressive**

**Is it ambiguous?** ✗ NO
- Exactly represents the selection
- Multiple indices have clear meaning (all are selected)

**Code that reads this field**:
- ✓ `SelectionResolver.resolve()` - returns it as-is
- ✓ `BaseAction.action_index` property - uses `[0]` for tie-breaking
- ✓ `ReplayLogger._action_to_record()` - logs it via action_index
- ✓ `ActionTraceCollector._describe_action()` - doesn't use it
- ✓ Tests - verify it's a tuple

**Status**: ✓ NO CHANGES NEEDED

---

### 2. `kind: ActionKind`

**Current value for combination action**: `ActionKind.CHOOSE_CARD` (or similar)

**Meaning**: The semantic category of action.

**Is it still meaningful?** ✓ YES
- Single-select CHOOSE_CARD: "choose this card"
- Combination: "choose these cards together"
- **Same kind, same semantics**

**Is it ambiguous?** ✗ NO
- Kind describes the action category
- Multiple selected_indices don't change the category

**Code that reads this field**:
- ✓ Rules filter by kind (e.g., `isinstance(action, PlayCardAction)`)
- ✓ ReplayLogger uses kind for action_type
- ✓ All code treats kind as semantic classifier
- **No code assumes single selection based on kind**

**Status**: ✓ NO CHANGES NEEDED

---

### 3. `option: OptionReference`

**Critical issue identified**

**Current value for combination action**: Which OptionReference?
- Option 0 (Pikachu)?
- Option 1 (Charizard)?
- Both??

**Is it still meaningful?** ✗ PROBLEMATIC
- Single-select: `option` points to the one chosen
- Combination: `option` is ambiguous - which one does it represent?
- **SEMANTIC MISMATCH**

**Is it ambiguous?** ✓ YES - MAJOR AMBIGUITY
- Field name is singular: "option"
- But action selects multiple indices
- If we store option 0, why not option 1?
- If we store both, how? (field is single OptionReference)

**Code that reads this field**:
- ✓ ActionFactory stores it (in base_kwargs)
- ✓ Tests verify it exists
- ✓ **NOBODY reads it** (search shows no uses of `action.option`)

**Analysis**: 
- The `option` field is metadata-only, not used for logic
- It was used during ActionFactory construction but not referenced afterward
- **Can be left as first option (option[selected_indices[0]])**
- Or can be None for combinations
- Or can be removed entirely

**Status**: ⚠️ DESIGN DECISION NEEDED - Not broken, but semantically unclear

---

### 4. `selection_context: SelectContext`

**Current value for combination action**: `SelectContext.TO_HAND` (or similar)

**Meaning**: The context/zone of selection.

**Is it still meaningful?** ✓ YES
- Identifies which gameplay context this selection occurred in
- Single-select TO_HAND: select one card from hand
- Combination TO_HAND: select multiple cards from hand
- **Same context, same semantics**

**Is it ambiguous?** ✗ NO
- Context is independent of how many indices are selected

**Code that reads this field**:
- ✓ SelectionResolver uses it (already constraint-aware per our analysis)
- ✓ Rules use it for context-based filtering
- ✓ Analysis/trace code uses it

**Status**: ✓ NO CHANGES NEEDED

---

### 5. `selection_type: SelectType`

**Current value for combination action**: `SelectType.ZONE` (or similar)

**Meaning**: The type of selection (ZONE, PLAYER, etc.).

**Is it still meaningful?** ✓ YES
- Classifies the selection type
- Independent of single vs. multi-select

**Code that reads this field**:
- ✓ Used for context classification
- ✓ No assumptions about count

**Status**: ✓ NO CHANGES NEEDED

---

### 6. `metadata: dict[str, object]`

**Current value for combination action**: First option's metadata? Merged? Empty?

**Meaning**: Free-form metadata about the option.

**Is it still meaningful?** ✓ PROBABLY
- Combination action stores metadata dict
- For single-select: metadata of that one option
- For combination: metadata of first option (or merged, or empty)

**Is it ambiguous?** ✗ UNCLEAR
- Should combination action have:
  - First option's metadata?
  - All options' metadata?
  - Empty dict?
  - Merged dict?

**Code that reads this field**:
- ✓ Minimal usage (mostly stored, not read)
- ✓ No code iterates `metadata` keys expecting specific structure

**Status**: ⚠️ MINOR - Design decision, but not used heavily

---

## SUBCLASS FIELD ANALYSIS

### For CardChoiceAction (most relevant for combinations)

**Fields inherited from ChoiceAction**:
```python
chosen_card: Card | None = None
chosen_zone: Zone | None = None
chosen_index: int | None = None
chosen_owner: PlayerSide | None = None
chosen_number: int | None = None
chosen_energy_count: int | None = None
chosen_status_condition: StatusCondition | None = None
```

#### 7. `chosen_card: Card | None`

**Current value for combination**: Which card?

**Is it still meaningful?** ✗ AMBIGUOUS
- Single-select: the card chosen
- Combination: multiple cards chosen, but field is singular
- **SEMANTIC MISMATCH**

**Is it ambiguous?** ✓ YES
- Field name: "chosen_card" (singular)
- Value could be: first card? all cards? None?

**Code that reads this field**:
- ✓ **NOBODY READS IT** (search: no uses of `action.chosen_card`)
- ✓ Used in ActionFactory construction for metadata only
- ✓ Not read by rules, resolver, or analysis code

**Status**: ✓ SAFE - Not used, can be set to first card or None

---

#### 8. `chosen_zone: Zone | None`

**Current value for combination**: Which zone?

**Is it still meaningful?** ✗ AMBIGUOUS
- Single-select: the zone the card came from
- Combination: all cards from same zone? different zones?

**Code that reads this field**:
- ✓ **NOBODY READS IT** (no occurrences found)
- ✓ Used in construction only

**Status**: ✓ SAFE - Can be set to first card's zone or None

---

#### 9. `chosen_index: int | None`

**Current value for combination**: Which index?

**Is it still meaningful?** ✗ AMBIGUOUS
- Single-select: position in the zone
- Combination: positions of all cards?

**Code that reads this field**:
- ✓ **NOBODY READS IT** (no occurrences)

**Status**: ✓ SAFE - Can be set to first card's index or None

---

#### 10. `chosen_owner: PlayerSide | None`

**Current value for combination**: Owner of selected cards?

**Is it still meaningful?** ✓ YES
- All cards in same selection typically have same owner
- Can represent "cards chosen from this player"

**Status**: ✓ SAFE - Can be set to owner of selection

---

### For Attack/Evolution/Retreat Actions

#### 11. `target_pokemon: Pokemon | None`

**Only appears in**: AttackAction, EvolutionAction, RetreatAction

**Is it meaningful for combinations?** N/A
- These actions are typically single-select
- TO_HAND selections don't use these action types
- Combinations most relevant for CardChoiceAction

**Code that reads this field**:
- ✓ Evolution rule: scores by `action.target_pokemon`
- ✓ Retreat rule: scores by `action.target_pokemon`
- ✓ Analysis: checks target_pokemon values
- ✓ Description generation: displays target_pokemon.name

**Impact for combinations**: None (CardChoiceAction doesn't have target_pokemon)

**Status**: ✓ NO CHANGES NEEDED

---

#### 12. `card` (PlayCardAction, AttachEnergyAction)

**Only in**: PlayCardAction, AttachEnergyAction

**Is it meaningful for combinations?** N/A
- Used for single-card actions
- Combinations would use CardChoiceAction

**Code that reads this field**:
- ✓ Rules filter: `action.card.metadata.is_supporter()`
- ✓ Rules score: `supporter_score(action.card)[0]`
- ✓ Description: `f"Play: {action.card.name}"`

**Impact for combinations**: None

**Status**: ✓ NO CHANGES NEEDED

---

#### 13. `evolution_card` (EvolutionAction)

**Only in**: EvolutionAction

**Is it meaningful for combinations?** N/A
- Single-card evolution
- Not relevant for combinations

**Code that reads this field**:
- ✓ Evolution rule: `evolution_board_value(action.target_pokemon, action.evolution_card)`
- ✓ Description: `f"Evolve: {action.evolution_card.name}"`

**Status**: ✓ NO CHANGES NEEDED

---

## ACTION_INDEX PROPERTY ANALYSIS

**Current implementation**:
```python
@property
def action_index(self) -> int:
    return self.selected_indices[0] if self.selected_indices else -1
```

**For combination action `(0, 1)`**: Returns 0

**Is it meaningful?** ✓ YES
- Represents primary/first selection
- Used for tie-breaking in rules
- Used for logging

**Code that reads this property**:
- ✓ Rules: `sorted(actions, key=lambda a: (-score, a.action_index))`
- ✓ ReplayLogger: `f"Attack #{action.action_index}"`
- ✓ Validation: `if action_index < 0 or action_index >= len(...)`
- ✓ Tests: verify it returns first index

**Analysis**:
- ✓ Property works perfectly for combinations
- ✓ Returns first index as tie-breaker
- ✓ Fair and intuitive
- ✓ Backward compatible

**Status**: ✓ NO CHANGES NEEDED

---

## COMPREHENSIVE FIELD USE SCAN

### Fields NEVER read by external code:
- `option` (OptionReference) - **NEVER READ**
- `chosen_card` (CardChoiceAction) - **NEVER READ**
- `chosen_zone` (CardChoiceAction) - **NEVER READ**
- `chosen_index` (CardChoiceAction) - **NEVER READ**
- `metadata` (dict) - **RARELY READ**, not iterated

### Fields READ only during serialization/logging:
- `action_index` - used for tie-breaking and logs
- `kind` - used for type checking and classification
- `selection_context` - used for context dispatch
- `target_pokemon` - used in description/rules (different action types)
- `card` - used in description/rules (different action types)

### Fields READ by rules for scoring:
- `target_pokemon` - Evolution/Retreat/Knockout rules
- `card` - Supporter/Stadium/Item rules
- `action_index` - Tie-breaking in all rules
- `evolution_card` - Evolution rule

### Critical insight:
**No code reads `action.option` or the `chosen_*` fields of CardChoiceAction except during construction.**

All semantic information comes from:
1. `selected_indices` (the key field)
2. `kind` (action category)
3. `target_pokemon`, `card`, `evolution_card` (entity references)
4. Subclass type (determined by kind)

---

## BACKWARD COMPATIBILITY ANALYSIS

### Single-select actions (existing):
```
Action(selected_indices=(0,), kind=CHOOSE_CARD, chosen_card=Pikachu, ...)
```

### Combination actions (new):
```
Action(selected_indices=(0, 1), kind=CHOOSE_CARD, chosen_card=Pikachu, ...)
```

**Comparison**:

| Component | Single | Combo | Compatible? |
|-----------|--------|-------|-------------|
| selected_indices | (0,) | (0,1) | ✓ YES - all code handles tuples |
| action_index | 0 | 0 | ✓ YES - returns first index |
| kind | CHOOSE_CARD | CHOOSE_CARD | ✓ YES - same |
| chosen_card | Pikachu | Pikachu | ✓ YES - first card or None |
| Rules filtering | isinstance check | isinstance check | ✓ YES - works for both |
| Rules scoring | action.card.metadata | action.card.metadata | ✓ YES - first card metadata |
| Tie-breaking | -action.action_index | -action.action_index | ✓ YES - first index |
| Logging | action_index | action_index | ✓ YES - logs first index |

---

## THE CRITICAL FINDING

### Can BaseAction represent BOTH single-select and multi-select?

**YES - With one caveat:**

The current BaseAction data model is **structurally compatible** with combination actions because:

1. ✓ `selected_indices` already supports tuples of any length
2. ✓ `action_index` property already handles multiple indices
3. ✓ All scoring rules use `action_index` for tie-breaking (first index)
4. ✓ Card metadata is accessed via first card (or ignored)
5. ✓ Kind is independent of selection count
6. ✓ Selection context is independent of selection count

### The caveat: `option` field is ambiguous for combinations

**The problem**:
```python
# Single-select:
action.option = OptionReference(card=Pikachu)  # Clear

# Combination:
action.option = OptionReference(card=???)  # Which option?
```

**The solution - three options**:

#### Option 1: Store first option (recommended)
```python
action.option = OptionReference(card=Pikachu)  # First selected option
# Semantics: "option[0] is the primary option for this action"
# Already done: chosen_card also set to first option
# Impact: Minimal (option field unused)
```

#### Option 2: Set option to None for combinations
```python
action.option = None  # Indicates "multiple options"
# Semantics: "option is undefined for combinations"
# Impact: Code must handle None option (already does)
```

#### Option 3: Deprecate option field
```python
# Mark as deprecated, set to None always for new code
# Only maintain for backward compat
```

---

## FIELD-BY-FIELD SUMMARY TABLE

| Field | Type | Single-Select | Combination | Works? | Ambiguous? | Used? | Action |
|-------|------|---|---|---|---|---|---|
| selected_indices | tuple[int,...] | (0,) | (0,1) | ✓ | ✗ | ✓ | Keep as-is |
| kind | ActionKind | CHOOSE_CARD | CHOOSE_CARD | ✓ | ✗ | ✓ | Keep as-is |
| option | OptionReference | option[0] | ? | ⚠️ | ✓ | ✗ | Set to first option |
| selection_context | SelectContext | TO_HAND | TO_HAND | ✓ | ✗ | ✓ | Keep as-is |
| selection_type | SelectType | ZONE | ZONE | ✓ | ✗ | ✓ | Keep as-is |
| metadata | dict | first metadata | first metadata | ✓ | ✗ | ✗ | Keep as-is |
| chosen_card | Card\|None | Card | Card (first) | ✓ | ✗ | ✗ | Set to first card |
| chosen_zone | Zone\|None | Zone | Zone (first) | ✓ | ⚠️ | ✗ | Set to first zone |
| chosen_index | int\|None | int | int (first) | ✓ | ⚠️ | ✗ | Set to first index |
| chosen_owner | PlayerSide\|None | PlayerSide | PlayerSide | ✓ | ✗ | ✗ | Keep consistent |
| target_pokemon | Pokemon\|None | (N/A) | (N/A) | N/A | N/A | N/A | N/A |
| card | Card\|None | (N/A) | (N/A) | N/A | N/A | N/A | N/A |
| evolution_card | Card\|None | (N/A) | (N/A) | N/A | N/A | N/A | N/A |
| action_index | property | 0 | 0 (first) | ✓ | ✗ | ✓ | Keep as-is |

---

## DOES BASEACTION NEED GENERALIZATION?

### Answer: **NO - BaseAction data model is sufficient**

**Reasoning**:

1. **selected_indices already represents variable cardinality**
   - It's a tuple, can be length 1 or N
   - All code already handles tuples
   - No change needed

2. **All code that reads fields already handles both cases**
   - Uses `action.action_index` (first index, works for all)
   - Uses `kind` (independent of count)
   - Uses subclass type (independent of count)
   - Uses metadata fields on first card (sufficient)

3. **Unused fields don't break anything**
   - `option`, `chosen_card`, `chosen_zone`, `chosen_index` are not read
   - Can be set to "first selected option" semantics
   - Or set to None
   - Or left as-is

4. **The architecture already separates concerns correctly**
   - BaseAction stores "what was selected" (selected_indices)
   - SelectionResolver serializes "what was selected" (selected_indices)
   - Rules score based on "what kind of action" (kind, first card metadata)
   - None of these care about single vs. multiple

5. **No hidden assumptions will break**
   - `action_index` property: ✓ works (returns first)
   - Rules use `action.action_index`: ✓ works (first index)
   - Tie-breaking: ✓ works (first index)
   - Logging: ✓ works (first index + kind)
   - Validation: ✓ works (indices must be in legal_actions)

---

## WHAT WOULD NEED TO CHANGE

### In ActionFactory:
- ✓ Generate combinations (new logic)
- ✓ For each combination, set:
  - `selected_indices = (idx0, idx1, ...)`
  - `option = options[idx0]` (first option)
  - `chosen_card = options[idx0].card` (first card)
  - `chosen_zone = options[idx0].zone` (first zone)
  - etc.

### In SelectionResolver:
- ✓ Return `action.selected_indices` as-is (already works)

### In DecisionEngine:
- ✓ No changes (chooses one action, that action now can have multiple indices)

### In Rules:
- ✓ No changes (score by kind and first card, works for combinations)

### In ReplayLogger:
- ✓ No changes required (logs action_index, works for combinations)
- ⚠️ Optional: enhance to show all indices

### In Tests:
- ✓ Add tests for combination actions
- ✓ Verify selected_indices is tuple of length N
- ✓ Verify action_index returns first index
- ✓ Verify backward compat properties

---

## CONCLUSION

### Can BaseAction continue representing BOTH single-selection and multi-selection without changing its data model?

**YES**

**Evidence**:
1. ✓ `selected_indices` already supports variable length
2. ✓ All code that reads action fields uses `action_index` (first index)
3. ✓ No code makes assumptions about `selected_indices` length being 1
4. ✓ Unused fields (`option`, `chosen_*`) can be set via "first selected" semantics
5. ✓ All existing rules work unchanged
6. ✓ All existing serialization works unchanged
7. ✓ All validation works unchanged

### Does BaseAction itself need a generalized representation?

**NO**

**Why not**:
- The current representation already IS general (tuple of indices)
- The subclass fields (card, target_pokemon, etc.) are specific to action type, not to single vs. multi
- Combination actions are still single actions from DecisionEngine's perspective
- No new field types needed
- No structural changes needed

### Minimal changes required:

1. **ActionFactory**: Generate combinations + set fields to "first option" semantics
2. **SelectionResolver**: Already works (return selected_indices)
3. **Tests**: Add combo tests
4. **Everything else**: No changes needed

### The data model is elegant because:
- It separates "what indices were selected" from "which action was best"
- It lets DecisionEngine choose one complete action
- That one action fully represents a complete gameplay decision
- SelectionResolver just serializes what's already there
- Rules only care about action type and first card
- Tie-breaking works on first index

**No redesign of BaseAction is necessary.**

