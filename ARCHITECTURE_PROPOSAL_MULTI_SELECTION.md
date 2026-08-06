# Architecture Proposal: Multi-Selection Action Support

## Problem Analysis

### 1. Where the Abstraction is Wrong Today

**Current Assumption**: `one option = one action`

```python
SelectPrompt(
    minCount=1, maxCount=1,
    options=[opt0, opt1, opt2]
)
  ↓
ActionFactory creates:
  BaseAction(selected_indices=(0,), ...)
  BaseAction(selected_indices=(1,), ...)
  BaseAction(selected_indices=(2,), ...)
  ↓
DecisionEngine picks ONE action
  ↓
Agent returns ONE tuple[int, ...]
```

**The Mismatch**:
- The environment contract is: `list[int]` (arbitrary-length selection)
- The system design is: one action = one integer selection
- When `minCount=2, maxCount=2`, no single action represents the full legal move `[0, 1]`
- Generating all combinations creates combinatorial explosion:
  - 3 options, minCount=1: 3 actions
  - 3 options, minCount=2: 3 actions
  - 3 options, minCount=2, maxCount=3: **C(3,2) + C(3,3) = 3 + 1 = 4 actions**
  - 60 options (deck size), minCount=2, maxCount=2: **C(60,2) = 1,770 actions** ❌

### 2. Core Insight: The Action Should Represent a Strategy, Not an Option

**Key Realization**:
- Today: Action = "I choose option at index 0"
- Correct: Action = "My strategy is to select [0,1]" (possibly computed by agent)
- Problem: We're asking `DecisionEngine` to pick 1 action from a set
- Solution: The action itself should be the complete list of selections

---

## Proposed New Abstraction

### Three-Layer Model

#### Layer 1: **Selection** (What the environment provides)
```python
SelectPrompt:
  minCount: int          # Lower bound
  maxCount: int          # Upper bound
  options: [opt0, ...]   # Available indices
```

#### Layer 2: **Action** (What the decision system works with)
```python
BaseAction (NEW):
  kind: ActionKind
  strategy: SelectionStrategy  # ← NEW: How to select from options
  
class SelectionStrategy:
  """Represents how to select indices from available options."""
  
  @abstractmethod
  def select_indices(self, selection: SelectPrompt) -> tuple[int, ...]:
    """Compute the selected indices given the SelectPrompt."""
    pass
```

#### Layer 3: **Execution** (What the environment receives)
```python
ActionSelection:
  selected_option_indices: tuple[int, ...]  # The computed result
```

### Why This Solves the Problem

**Single-Selection Example**:
```python
class IndexSelectionStrategy(SelectionStrategy):
  def __init__(self, index: int):
    self.index = index
  
  def select_indices(self, selection: SelectPrompt) -> tuple[int, ...]:
    return (self.index,)
    
# Creates 1 action per option
ActionFactory:
  IndexSelectionStrategy(0) → selects [0]
  IndexSelectionStrategy(1) → selects [1]
  IndexSelectionStrategy(2) → selects [2]
```

**Multi-Selection Example**:
```python
class PairSelectionStrategy(SelectionStrategy):
  def __init__(self, index1: int, index2: int):
    self.index1 = index1
    self.index2 = index2
  
  def select_indices(self, selection: SelectPrompt) -> tuple[int, ...]:
    if len([self.index1, self.index2]) >= selection.min_count:
      return (self.index1, self.index2)
    return ()  # Invalid
    
# Creates ONLY valid combinations
ActionFactory:
  PairSelectionStrategy(0, 1) → selects [0, 1]
  PairSelectionStrategy(0, 2) → selects [0, 2]
  PairSelectionStrategy(1, 2) → selects [1, 2]
  # Total: 3 actions (not 1,770)
```

**Agent Decision Example**:
```python
class RuleBasedSelectionStrategy(SelectionStrategy):
  def __init__(self, rule_fn):
    self.rule_fn = rule_fn
  
  def select_indices(self, selection: SelectPrompt) -> tuple[int, ...]:
    # Agent logic computes the selection
    return self.rule_fn(selection)
    
# Creates 1 action: "apply this rule"
ActionFactory:
  RuleBasedSelectionStrategy(decide_prize_cards) → selects what rule decides
```

---

## Impact on Each Component

### ActionFactory

**Current**:
```python
def from_selection(selection: SelectPrompt) -> tuple[BaseAction, ...]:
  actions = []
  for option_index in range(len(selection.options)):
    actions.append(BaseAction(selected_indices=(option_index,)))
  return actions
```

**New**:
```python
def from_selection(selection: SelectPrompt) -> tuple[BaseAction, ...]:
  # Single-selection: create one strategy per option
  if selection.minCount == 1 and selection.maxCount == 1:
    return (
      CardChoiceAction(strategy=IndexSelectionStrategy(i), ...)
      for i in range(len(selection.options))
    )
  
  # Multi-selection: create strategies for valid combinations
  # OR create one agent-based strategy that decides at evaluation time
  else:
    # Option A: Generate combinations (only for small counts)
    if selection.maxCount <= 2 and len(selection.options) <= 10:
      strategies = [CombinationSelectionStrategy(indices, selection) 
                    for indices in valid_combinations(selection)]
      return [CardChoiceAction(strategy=s, ...) for s in strategies]
    
    # Option B: Defer to agent at evaluation time (recommended)
    else:
      return (CardChoiceAction(strategy=DeferredSelectionStrategy(), ...),)
```

**Complexity**: ✅ LOW
- No breaking changes to existing single-select logic
- Multi-select paths are new, not modifications
- Can grow incrementally

### DecisionEngine

**Current**:
```python
def decide(context: DecisionContext) -> DecisionOutcome:
  for rule in rules:
    result = rule.evaluate(context)  # Returns BaseAction
    if result.passed:
      return result.selected_action  # ONE action
```

**New** (no change to engine itself!):
```python
def decide(context: DecisionContext) -> DecisionOutcome:
  # Same logic - still selects ONE action
  # The action now contains a strategy instead of indices
  for rule in rules:
    result = rule.evaluate(context)
    if result.passed:
      return result.selected_action  # ONE action with strategy
```

**Complexity**: ✅ ZERO (no changes needed)
- Decision logic unchanged
- Still picks one action
- Strategy is evaluated later

### Rules

**Current**:
```python
class MyRule(BaseRule):
  def evaluate(self, context: DecisionContext) -> RuleResult:
    # Selects from context.legal_actions (tuple of BaseAction)
    # Returns ONE action
    action = context.legal_actions[0]
    return self._result(passed=True, action=action)
```

**New**:
```python
class MyRule(BaseRule):
  def evaluate(self, context: DecisionContext) -> RuleResult:
    # Selects from context.legal_actions (tuple of BaseAction)
    # Returns ONE action
    action = context.legal_actions[0]  # Same as before
    return self._result(passed=True, action=action)
```

**Complexity**: ✅ ZERO (no changes needed)
- Rules don't care about selection strategies
- Rules still pick one action
- Strategy is opaque to rules

### BaselineAgent

**Current**:
```python
def act(self, observation: Observation) -> ActionSelection:
  selected_action = decision_engine.decide(context)
  return ActionSelection(
    selected_option_indices=selected_action.selected_indices
  )
```

**New**:
```python
def act(self, observation: Observation) -> ActionSelection:
  selected_action = decision_engine.decide(context)
  # NEW: Evaluate the strategy to get actual indices
  indices = selected_action.strategy.select_indices(
    observation.selection
  )
  return ActionSelection(selected_option_indices=indices)
```

**Complexity**: ✅ LOW
- One-line change to evaluate strategy
- No other logic changes

---

## How It Supports Future Use Cases

### MCTS (Monte Carlo Tree Search)

**Current Problem**: Exploding action space at root node
- 60 deck options, multi-select: 1,770+ actions per state

**With Strategy Abstraction**:
```python
class MCTSSelectionStrategy(SelectionStrategy):
  def __init__(self, state_hash, node_index):
    self.state_hash = state_hash
    self.node_index = node_index
  
  def select_indices(self, selection: SelectPrompt) -> tuple[int, ...]:
    # Look up which indices were selected in MCTS tree at this node
    return tree.get_action_for_node(self.state_hash, self.node_index)

# ActionFactory creates ONE action per MCTS node, not per combination
ActionFactory:
  MCTSSelectionStrategy(state1, node0) → [0, 1]
  MCTSSelectionStrategy(state1, node1) → [0, 2]
  # Branches stored in tree, not in action count
```

### RL (Reinforcement Learning)

**Problem**: Policy outputs N actions, not one

**With Strategy Abstraction**:
```python
class RLSelectionStrategy(SelectionStrategy):
  def __init__(self, policy_output):
    self.policy_output = policy_output
  
  def select_indices(self, selection: SelectPrompt) -> tuple[int, ...]:
    # Post-process policy output to satisfy constraints
    return constrain_to_limits(
      self.policy_output,
      min_count=selection.min_count,
      max_count=selection.max_count
    )

# ActionFactory creates ONE action that wraps the policy
ActionFactory:
  RLSelectionStrategy(policy_output) → post-processes and returns valid selection
```

### Search (A*, BFS, DFS)

**Problem**: Need to represent all possible selections at once

**With Strategy Abstraction**:
```python
class SearchSpaceSelectionStrategy(SelectionStrategy):
  def __init__(self, search_node_id):
    self.search_node_id = search_node_id
  
  def select_indices(self, selection: SelectPrompt) -> tuple[int, ...]:
    # Look up which selection this search node represents
    return search_graph.get_selection(self.search_node_id)

# ActionFactory creates ONE action per search node
# Search explores the graph, not the action space
ActionFactory:
  SearchSpaceSelectionStrategy(node_0) → represents one search branch
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (2-3 hours)

1. **Define SelectionStrategy interface**
   - Abstract base class
   - One method: `select_indices(SelectPrompt) → tuple[int, ...]`

2. **Create concrete strategies**
   - `IndexSelectionStrategy(index)` - selects single option
   - `DeferredSelectionStrategy()` - placeholder for later logic

3. **Modify BaseAction**
   - Add `strategy: SelectionStrategy` field
   - Keep `selected_indices` for backward compat (computed property)

4. **Update ActionFactory**
   - Single-select path: create `IndexSelectionStrategy(i)` for each option
   - Keep API unchanged (returns same action count)

5. **Update BaselineAgent.act()**
   - Call `action.strategy.select_indices(observation.selection)`
   - Return computed indices to environment

### Phase 2: Multi-Selection Support (1-2 hours)

1. **Implement CombinationSelectionStrategy**
   - Generates valid combinations for minCount/maxCount
   - Add to ActionFactory when appropriate

2. **Add validation**
   - Verify constraints are satisfied
   - Return empty tuple for invalid selections

### Phase 3: Advanced Strategies (As Needed)

1. MCTS strategy wrapper
2. RL strategy wrapper
3. Search strategy wrapper

---

## Complexity Estimates

| Component | Current | Proposed | Change | Effort |
|-----------|---------|----------|--------|--------|
| **BaseAction** | 1 field | +1 field | Additive | 1 hour |
| **ActionFactory** | Lines: 60 | Lines: 80 | +20 LOC | 1 hour |
| **DecisionEngine** | N/A | N/A | No change | 0 hours |
| **Rules** | N/A | N/A | No change | 0 hours |
| **BaselineAgent.act()** | 1 line | 3 lines | +2 lines | 15 min |
| **Test updates** | N/A | N/A | No change | 0 hours |
| **SelectionStrategy** | N/A | New | 200-300 LOC | 2 hours |
| **Total** | - | - | - | **~4-5 hours** |

---

## Key Advantages

✅ **No breaking changes**: Backward compatible via computed property  
✅ **No action explosion**: Single-select stays 1 action per option  
✅ **No combinatorial growth**: Multi-select uses strategies, not combinations  
✅ **Agent-centric**: Agent logic moves to strategy, not factory  
✅ **Extensible**: MCTS/RL/Search strategies are just implementations  
✅ **Rule-neutral**: Rules unchanged, no special-casing needed  
✅ **Lazy evaluation**: Indices computed at execution time, not at factory time  

---

## Alternative Approaches (Why This is Best)

### Alternative 1: Generate All Combinations
- ❌ Combinatorial explosion (1,770 actions for prize selection)
- ❌ Doesn't solve MCTS/RL/Search problem
- ❌ Breaks scalability

### Alternative 2: Return Action Index + "Select Mode"
```python
BaseAction(
  action_index=0,
  mode="multi_select",
  num_to_select=2
)
```
- ❌ Unclear which 2 of 3 options to select
- ❌ Agent still doesn't know the selection
- ❌ Defers problem to agent logic

### Alternative 3: Move All Logic to Agent
```python
def act(observation) -> list[int]:
  # Agent decides directly, no ActionFactory
```
- ❌ Breaks decision engine pipeline
- ❌ Loses abstraction and testability
- ❌ Rules can't participate

---

## Recommendation

**Use the SelectionStrategy abstraction.**

It is the cleanest design that:
1. Solves single-selection (no change needed)
2. Enables multi-selection (strategies for combinations)
3. Scales to MCTS (strategy per tree node)
4. Scales to RL (strategy wraps policy)
5. Scales to Search (strategy per search node)
6. Requires minimal code changes
7. Maintains all existing abstractions

The design is based on the insight that **the decision engine's job is to pick one strategy, and that strategy's job is to map options to a selection**.
