# Action Pipeline Instrumentation Guide

## Overview

This document describes the instrumentation added to identify illegal actions returned to the cabt environment. The goal is to identify the EXACT FIRST illegal action with complete evidence-based analysis.

## Instrumentation Architecture

### 1. Action Trace Collection (`src/poketcg/debug/action_trace.py`)

**Purpose**: Capture detailed information about every action decision.

**Components**:
- `ActionTraceEntry`: Dataclass storing one decision's full context
- `ActionTraceCollector`: Accumulates traces across a game
- `get_trace_collector()`: Global instance for easy access
- `reset_trace_collector()`: Resets for new games

**Captured Information per Decision**:
```
- Turn: Game turn number
- Step: Sequential decision within turn  
- Player: Which player (0 or 1)
- Select Type: MAIN, ATTACK_TARGET, etc.
- Select Context: MAIN, BENCH_SELECT, etc.
- Legal Option Count: Number of valid choices
- Raw select.option: The exact options from observation
- Parsed Actions: Actions created by ActionFactory
- Chosen Action: Which action the decision engine selected
- Returned Integer: The index returned to the environment
- Validation Status: Did our validation checks pass?
- Validation Error: If failed, what was wrong?
- Decision Error: Any errors from the decision engine?
```

### 2. Baseline Agent Tracing (`src/poketcg/agent/baseline.py`)

**Three-Layer Validation**:

#### Layer 1: Null Check (`_validate_action_legality`)
- Verifies the selected action object exists
- If None, falls back to first legal action

#### Layer 2: Bounds Check  
- Verifies `action_index` is in range `[0, len(legal_actions) - 1]`
- If out of bounds, falls back to first legal action

#### Layer 3: Identity Check
- Verifies the selected action object IS in the legal_actions tuple
- Uses both object identity (via `is`) and equality check
- If mismatch, falls back to first legal action

**Decision Tracing** (`_trace_action_decision`):
- Called after validation passes
- Records all decision information to the global trace collector
- Includes additional checks for action-in-legal-actions validation

**Game Lifecycle**:
- `_ensure_game_started()`: Resets trace collector for new game
- `_finish_replay_if_terminal()`: Prints trace summary and exports JSON

### 3. Trace Analysis (`analyze_traces.py`)

**Purpose**: Analyze collected traces to find illegal actions.

**Capabilities**:
- Loads all `trace_*.json` files from `outputs/replays/`
- Checks each decision for:
  - Out-of-bounds returned integers
  - Validation failures
  - Decision engine errors
- Generates detailed reports
- Cross-file summary

**Usage**:
```bash
python analyze_traces.py
```

## Data Flow

```
Observation
    ↓
ObservationParser.parse()
    ↓
ActionFactory.from_observation() → Actions with indices [0, 1, 2, ...]
    ↓
DecisionContext.legal_actions
    ↓
DecisionEngine.decide() → Returns one of the legal actions
    ↓ (with identity validation)
_choose_action() → Returns the chosen action
    ↓
_validate_action_legality() → Three-layer validation
    ↓ (if valid)
_trace_action_decision() → Record to trace collector
    ↓
act() returns ActionSelection(selected_option_indices=(returned_integer,))
    ↓
main.py → cabt environment
```

## What Each Validation Layer Catches

### Layer 1: Null Check
- **Catches**: Decision engine returns None
- **Evidence**: `validation_error` = "Selected action is None"
- **Root Cause**: Rule didn't actually select an action

### Layer 2: Bounds Check
- **Catches**: `action_index` outside [0, N-1]
- **Evidence**: `validation_error` = "Index {X} out of bounds [0, {N-1}]"
- **Root Cause**: Action index corrupted or decision engine error

### Layer 3: Identity Check
- **Catches**: Action object not in legal_actions tuple
- **Evidence**: `validation_error` = "Chosen action object not in legal_actions"
- **Root Cause**: Either:
  - Decision engine returned wrong action
  - Action object was modified/mutated after selection
  - Stale reference from previous observation

## Running with Tracing Enabled

### Local Testing

```bash
# Enable replay logging (which includes tracing)
python run_local.py --games 5 --replay
```

This will:
1. Create `outputs/replays/` directory
2. Generate `trace_game_*.json` files (one per game)
3. Print trace summaries to console
4. Show HTML replays

### Analyzing Results

```bash
python analyze_traces.py
```

This will:
1. Read all trace files
2. Find any illegal actions
3. Report turn/player/details
4. Show cross-file summary
5. Indicate if issue only happens sometimes

## Expected Output Format

### Trace File (`trace_game_001.json`)

```json
[
  {
    "turn": 4,
    "step": 0,
    "player_index": 1,
    "select_type": "MAIN",
    "select_context": "MAIN",
    "legal_option_count": 3,
    "raw_select_option": [
      {"type": "END"},
      {"type": "ATTACK"},
      {"type": "PLAY"}
    ],
    "parsed_actions": [
      {
        "index": 0,
        "type": "EndTurnAction",
        "description": "End Turn"
      },
      ...
    ],
    "chosen_action": {
      "index": 0,
      "type": "EndTurnAction",
      "description": "End Turn"
    },
    "returned_integer": 0,
    "validation_passed": true,
    "validation_error": null,
    "decision_error": null
  },
  ...
]
```

### Analysis Output

If illegal actions are found:
```
ILLEGAL ACTIONS DETECTED:
Decision 15 (Turn 4, Player 1):
  Select Type: MAIN
  Returned Integer: 5
  Legal Range: [0, 2]
  Chosen Action: PlayCardAction
```

If none found:
```
✓ No illegal actions found in any trace files.

If games are still ending with INVALID status, the issue may be:
  - A constraint we're not capturing in the trace
  - An issue AFTER the action is returned (environment-side)
  - A mutation of the action object after validation
```

## Debugging Process

### Step 1: Identify Illegal Actions
```bash
python run_local.py --games 20 --replay
python analyze_traces.py
```

### Step 2: If Illegal Actions Found
Look at:
1. **Returned Integer vs Legal Range**: Is it truly out of bounds?
2. **Chosen Action Type**: What kind of action was selected?
3. **Turn/Player**: Does it happen at a specific turn? Player?
4. **Select Type**: Is it always the same selection type (MAIN, ATTACK_TARGET)?

### Step 3: If No Illegal Actions But INVALID Status Still Occurs
The issue is likely:
1. **Missing validation**: An additional constraint the environment checks but we don't
2. **Post-validation mutation**: Action modified after we return it
3. **Environment bug**: The environment's own validation is too strict
4. **Selection context mismatch**: We're returning a valid index but for wrong context

To investigate further:
- Compare `parsed_actions` vs `raw_select_option` - are they in sync?
- Check if `chosen_action.option.metadata` has required fields
- Verify `selection_context` and `selection_type` match what's expected

## Integration Points

### Files Modified
- `src/poketcg/agent/baseline.py`: Added tracing and enhanced validation
- `src/poketcg/debug/action_trace.py`: New trace collection system

### Files That Use Tracing
- `run_local.py`: Runs games and captures traces
- `main.py`: Submission entry point (tracing disabled in submission)

### Configuration
- Tracing is enabled when `replay=ReplayLoggerConfig(enabled=True, ...)`
- Traces are saved to `outputs/replays/trace_*.json`
- Can be disabled by setting `replay.enabled=False` in submission

## Success Criteria

**Instrumentation is working correctly when**:
1. Local games produce trace JSON files
2. Each trace has entries for every decision
3. Valid games show `validation_passed: true` for all decisions
4. Invalid games show which decision first failed validation
5. `analyze_traces.py` can identify the exact problematic action

**Debugged successfully when**:
1. All illegal actions are identified with evidence
2. Root cause is documented in trace data
3. Fix can be implemented based on identified cause
4. All games end with consistent results
