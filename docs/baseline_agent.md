# Baseline Agent Reference

This document describes the Phase 9 baseline agent.

Its job is:

```text
Raw Observation
      |
      v
ObservationParser
      |
      v
Typed Observation / GameState
      |
      v
ActionFactory
      |
      v
Typed Actions
      |
      v
GameAnalyzer
      |
      v
DecisionContext
      |
      v
DecisionEngine
      |
      v
Rule Library
      |
      v
Chosen Action
      |
      v
Kaggle option index
```

The baseline agent is intentionally a thin orchestrator.

It does not:

- parse raw observations manually,
- implement gameplay rules itself,
- rank actions outside the rule engine,
- modify `GameState`,
- bypass typed actions or the analyzer.

## Main Files

- [src/poketcg/agent/baseline.py](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\agent\baseline.py)
- [src/poketcg/agent/config.py](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\agent\config.py)
- [src/poketcg/agent/factory.py](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\agent\factory.py)
- [src/poketcg/agent/lifecycle.py](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\agent\lifecycle.py)

## Responsibilities

The baseline agent is responsible for:

- selecting a deterministic valid deck,
- validating that deck before startup completes,
- detecting deck-selection versus gameplay observations,
- parsing gameplay observations,
- building typed actions,
- building the analyzer,
- building the decision context,
- invoking the decision engine,
- returning Kaggle-facing option indices,
- starting and finishing replay sessions,
- applying safe fallbacks when unexpected errors happen.

## Lifecycle

## Deck Selection

When the payload is the initial deck-selection handshake:

- no parsed state exists,
- no legal selection exists,
- the agent returns the deterministic baseline deck as a list of 60 card ids,
- the deck is validated against the shared deck subsystem during startup so illegal decks fail fast.

## Gameplay

For normal gameplay observations:

1. Parse the raw observation with `ObservationParser`.
2. Build typed legal actions with `ActionFactory`.
3. Build `GameAnalyzer`.
4. Build `DecisionContext`.
5. Run `DecisionEngine`.
6. Return the chosen action index in Kaggle format.

## Replay Integration

Replay logging is wired through the decision engine.

When decision logging is enabled:

- the replay logger records board state,
- the legal typed actions are captured,
- the chosen action is recorded,
- the decision trace is stored,
- the session is automatically finished when a terminal observation is seen.

## Error Handling

The baseline agent follows this fallback order:

1. `DecisionEngine`
2. explicit `FallbackRule`
3. first legal typed action
4. emergency raw first-option fallback only if typed parsing failed before any legal action could be built

That final raw fallback exists only to keep the submission boundary from crashing.

## Deterministic Deck

The baseline deck is intentionally simple and deterministic.

Current construction:

- 5 Basic Pok\u00e9mon with attacks, 4 copies each,
- 5 Trainer cards, 4 copies each,
- 20 matching Basic Energy cards distributed across the chosen Pok\u00e9mon types.

This deck builder is not an optimizer.

It only guarantees a stable 60-card deck for baseline gameplay.

It also avoids ACE SPEC copy-limit violations so the deck remains legal under the official `cabt` rules.

## Future Extension Points

Likely future additions:

- deck-loading from explicit deck lists or deck files,
- richer agent lifecycle telemetry,
- alternate agent factories for evaluation and self-play,
- strategy-specific agent subclasses that still reuse the same orchestration shell.
