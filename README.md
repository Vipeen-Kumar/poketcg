# poketcg

Production-oriented foundation for an AI Training Agent for Kaggle's "The Pokemon Company - PTCG AI Battle Challenge Simulation".

This repository is intentionally modular. The final Kaggle submission will eventually reduce to `main.py` and `deck.csv`, but development happens in a scalable codebase that can support:

- rule-based agents,
- Monte Carlo Tree Search,
- reinforcement learning,
- transformer policies,
- self-play training,
- evaluation and benchmarking.

## Project Status

Status: Core infrastructure plus first playable agent implemented

The repository now contains:

- environment documentation,
- modular project architecture,
- static English card database,
- raw observation parser,
- typed action abstraction layer,
- factual game analysis API,
- deterministic decision engine,
- PokÃ©mon rule library,
- replay and debug logging,
- the first fully playable baseline agent.

## Current Phase

Current completed phase: Phase 9 - Baseline Agent

This phase adds the first end-to-end playable agent that reuses the parser, action system, analyzer, decision engine, rule library, and replay logger to play legal games from start to finish.

## Completed Phases

- Phase 0 - Environment Documentation
- Phase 1 - Project Architecture
- Phase 2 - English Card Database
- Phase 3 - Observation Parser
- Phase 4 - Action System
- Phase 5 - Game Analysis API
- Phase 6 - Decision Engine
- Phase 7 - Replay And Debug Logging
- Phase 8 - Rule Library
- Phase 9 - Baseline Agent

## Major Modules Implemented

- `poketcg.domain`
  Stable internal models and enums used across the project.

- `poketcg.cards`
  Static English card metadata loading, normalization, validation, indexing, and search helpers.

- `poketcg.engine`
  Raw Kaggle observation parsing and environment-facing translation into typed internal state.

- `poketcg.actions`
  Conversion from parsed legal selections into typed action objects that preserve Kaggle option indices.

- `poketcg.analysis`
  Factual query layer over parsed observations and typed legal actions.

- `poketcg.decision`
  Deterministic rule execution, rule registration, fallback policy, and execution traces.

- `poketcg.rules`
  PokÃ©mon knowledge layer containing reusable gameplay rules and automatic rule registration.

- `poketcg.debug`
  Development-only replay capture, formatting, and replay file writing.

- `poketcg.agent`
  Thin submission-facing orchestration over deck selection, parsed gameplay decisions, and replay-integrated rule execution.

- `tests.cards`, `tests.engine`, `tests.actions`, `tests.analysis`, `tests.decision`, `tests.rules`, `tests.debug`, `tests.agent`, `tests.integration`
  Verification coverage for the currently implemented layers.

## Remaining Roadmap

- Stronger rule-based strategy layers.
- Search abstractions and MCTS.
- Encoding layer for model inputs and action representations.
- Reinforcement learning and self-play infrastructure.
- Evaluation and benchmarking systems.
- Final Kaggle submission packaging around `main.py` and `deck.csv`.

## Not Yet Implemented

- advanced heuristics,
- search behavior,
- model feature encoding,
- reinforcement learning,
- training loops,
- evaluation runners.

## Key Docs

- Environment reference: [docs/environment.md](C:\Users\vipee\Desktop\study\project\poketcg\docs\environment.md)
- Architecture reference: [docs/architecture.md](C:\Users\vipee\Desktop\study\project\poketcg\docs\architecture.md)
- Card database reference: [docs/card_database.md](C:\Users\vipee\Desktop\study\project\poketcg\docs\card_database.md)
- Parser reference: [docs/parser.md](C:\Users\vipee\Desktop\study\project\poketcg\docs\parser.md)
- Action system reference: [docs/actions.md](C:\Users\vipee\Desktop\study\project\poketcg\docs\actions.md)
- Analysis reference: [docs/analysis.md](C:\Users\vipee\Desktop\study\project\poketcg\docs\analysis.md)
- Decision engine reference: [docs/decision_engine.md](C:\Users\vipee\Desktop\study\project\poketcg\docs\decision_engine.md)
- Rules reference: [docs/rules.md](C:\Users\vipee\Desktop\study\project\poketcg\docs\rules.md)
- Debug logging reference: [docs/debug_logging.md](C:\Users\vipee\Desktop\study\project\poketcg\docs\debug_logging.md)
- Baseline agent reference: [docs/baseline_agent.md](C:\Users\vipee\Desktop\study\project\poketcg\docs\baseline_agent.md)
