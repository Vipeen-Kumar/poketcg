# Data Flow Analysis: Where Do Multiple Indices Come From?

**Date**: August 6, 2026  
**Question**: How can MultiSelectionResolver return [0, 1] when only one BaseAction containing (0,) is selected?

---

## CURRENT DATA FLOW (BROKEN FOR MULTI-SELECT)

```
Observation (minCount=2, maxCount=2, 3 options)
    ↓
ActionFactory.from_selection()
    → Creates 3 actions:
      - Action(selected_indices=(0,))
      - Action(selected_indices=(1,))
      - Action(selected_indices=(2,))
    ↓
DecisionContext.legal_actions = [Action(0,), Action(1,), Action(2,)]
    ↓
DecisionEngine.decide()
    → Rules evaluate all 3 actions
    → Rule selects ONE action: Action(0,)
    ↓
BaselineAgent.act()
    → validated_action = Action(0,)
    → selected_indices = (0,)
    ↓
SelectionResolver.resolve(action=Action(0,), selection.minCount=2)
    → PROBLEM: Returns only (0,) because action only has one index
    → SDK needs (0, 1) or (0, 2) or (1, 2)
    ↓
SDK receives [0]
    → INVALID (constraint violated: 1 < minCount=2)
```

**The Core Issue**: 
- ActionFactory creates one action per option
- DecisionEngine selects one action
- One action = one selected_index
- MultiSelectionResolver cannot magically create more indices

---

## SOLUTION ANALYSIS

### Option 1: ActionFactory Creates Combination Actions (NO)

Could ActionFactory create all combinations?
```python
# For 3 options with minCount=2, maxCount=2:
Action(selected_indices=(0, 1))
Action(selected_indices=(0, 2))
Action(selected_indices=(1, 2))
```

**Problems**:
- Combinatorial explosion: 3 options → 3 combinations, but 10 options → 45 combinations
- Not scalable for large option sets
- Would require DecisionEngine to understand combination semantics
- Rules would need to evaluate combinations, not individual options

**Status**: Not viable

---

### Option 2: DecisionEngine Selects Multiple Actions (NO)

Could DecisionEngine return a set of actions?
```python
selected_actions = [Action(0,), Action(1,)]  # Multiple actions
```

**Problems**:
- DecisionEngine is designed to return ONE action (RuleResult.selected_action is singular)
- Would require fundamental redesign of DecisionEngine
- Rules evaluate single actions, not sets
- Breaks the entire decision architecture
- User said: "Keep DecisionEngine, ActionFactory, Rule system unchanged"

**Status**: Not viable (violates constraints)

---

### Option 3: MultiSelectionResolver Constructs from Action Indices (YES - BUT INCOMPLETE)

**Current thinking**: MultiSelectionResolver has only one action, can't construct multiple indices.

**But wait**: What if MultiSelectionResolver gets MORE INFORMATION from elsewhere?

Let me check what information is available:

**MultiSelectionResolver receives**:
1. `action: BaseAction` → has selected_indices=(0,)
2. `selection: SelectPrompt` → has minCount=2, maxCount=2, options=[...]

**The key question**: Can MultiSelectionResolver use the Selection information to construct missing indices?

---

## REVEALING THE HIDDEN INFORMATION

Look at the Observation data carefully for minCount=2 case:

```
[CAPTURE-SEMANTIC] SelectContext.TO_HAND OBSERVATION
[CAPTURE-SEMANTIC] minCount=2, maxCount=2
[CAPTURE-SEMANTIC] Number of options: 3
[CAPTURE-SEMANTIC] Options (all JSON):
[
  {"type": 3, "area": 6, "index": 0, "playerIndex": 0},
  {"type": 3, "area": 6, "index": 1, "playerIndex": 0},
  {"type": 3, "area": 6, "index": 2, "playerIndex": 0}
]
```

**Key insight**: All 3 options are IDENTICAL SEMANTICALLY (all are prize cards from same player)

For TO_HAND (return to hand), if the rule says "choose prize 0", and the constraint says "minCount=2":
- The context means "return 2 prize cards to hand"
- The action says "the primary choice is prize 0"
- The constraints say "must choose exactly 2"
- The options say "can choose from [0, 1, 2]"

---

## WAIT - RETHINKING THE PROBLEM

Actually, let me reconsider: **What does the rule ACTUALLY CHOOSE for multi-select?**

For minCount=2, maxCount=2 (return 2 prize cards):
- Should ActionFactory create 1 action per PAIR?
- Or should DecisionEngine choose 2 different actions somehow?
- Or should the Rule know to select multiple options?

**Looking at the code again**: ActionFactory creates one action per OPTION, not per combination or scenario.

For TO_HAND with 3 prize options:
- ActionFactory creates: Action(0), Action(1), Action(2)
- DecisionEngine picks one: Action(0)
- But we need [0, 1] or [0, 2] or [1, 2]

**The rule selected Action(0), but for multi-select we need 2 actions selected.**

---

## THE REAL ANSWER

**The problem is architectural, not just at SelectionResolver level:**

**For minCount ≤ 1**: 
- One action = one index ✓
- GenericResolver: return action.selected_indices[0] ✓

**For minCount > 1**:
- Need MULTIPLE actions selected, but DecisionEngine returns ONE action
- ActionFactory creates N actions (one per option), but DecisionEngine picks 1
- Rule evaluates each action independently
- No component knows to pick 2 or more actions

---

## CRITICAL REALIZATION

**There is no mechanism to handle minCount > 1 in the current architecture.**

The fix requires ONE of these:

### Path A: ActionFactory Creates Combinations
- Create N choose minCount..maxCount actions
- DecisionEngine picks one
- MultiSelectionResolver unpacks it
- **Problem**: Combinatorial explosion, scalability

### Path B: DecisionEngine/Rules Select Multiple Actions
- Rule returns multiple selected_actions
- DecisionEngine handles multiple actions
- BaselineAgent gets multiple actions
- MultiSelectionResolver unpacks them
- **Problem**: Major redesign (violates constraints)

### Path C: MultiSelectionResolver Constructs from Constraints
- ActionFactory creates single actions as before
- DecisionEngine picks one action as before
- MultiSelectionResolver uses HEURISTIC to select additional indices
- E.g., "if minCount=2 and action=(0,), return (0, 1)"
- **Problem**: What's the heuristic? Pure guess is wrong!

### Path D: Rule System Awareness
- Rules know about minCount/maxCount
- Rules generate decisions that include multiple indices
- Need new action type or decision mechanism
- **Problem**: Major change to rule system

---

## WHAT THE FORENSIC DATA SHOWS

From the captured observation:
```
[CAPTURE-SEMANTIC] SelectContext.TO_HAND minCount=2
[CAPTURE-SEMANTIC] Options: 
  {index: 0, area: 6, playerIndex: 0}
  {index: 1, area: 6, playerIndex: 0}
  {index: 2, area: 6, playerIndex: 0}
```

These are 3 identical semantic options. The context is "return 2 of these 3 cards to hand".

**The rule has no special knowledge of this.** The rule operates on single options, not multi-select semantics.

---

## CONCLUSION BEFORE IMPLEMENTATION

**MultiSelectionResolver CANNOT magically produce [0, 1] from action=(0,) without additional information.**

Currently:
- ✓ ActionFactory can create actions (one per option)
- ✓ DecisionEngine can select one action
- ✗ No mechanism to create multi-index selections
- ✗ Rules don't understand "select 2"

**Before implementing MultiSelectionResolver, we must answer:**

**WHO determines that we should return [0, 1] instead of [0] alone?**

1. The Rule? (Rule evaluates each option independently, doesn't know about minCount > 1)
2. The ActionFactory? (Would need to create combinations)
3. The DecisionEngine? (Would need to select multiple actions)
4. A heuristic in MultiSelectionResolver? (But which heuristic?)

**The honest answer**: The current system has no component that selects "which 2 options" when minCount=2.

---

## REQUIRED DESIGN DECISION

Before implementing, we need to clarify:

**For a multi-select context (minCount=2):**

1. **Should ActionFactory create combination actions?**
   - Action(0,1), Action(0,2), Action(1,2)
   - Then DecisionEngine picks the best combination
   - Then MultiSelectionResolver unpacks it

2. **Should we add a multi-select action type?**
   - MultiSelectAction(selected_indices=(0, 1))
   - ActionFactory creates one per valid combination
   - Same flow as above

3. **Should the Rule system be made aware of minCount?**
   - Rules evaluate minCount=2 differently
   - Return multi-selection actions
   - Requires rule system changes

4. **Should MultiSelectionResolver make heuristic choices?**
   - ActionFactory creates single actions
   - DecisionEngine selects one
   - MultiSelectionResolver: "I have 1 index, need 2, so return (index, index+1)"
   - **This is DANGEROUS—no principled basis**

**We cannot implement a working solution without deciding this.**

