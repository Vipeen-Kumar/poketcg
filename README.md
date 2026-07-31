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

Status: Foundation layers implemented

The repository now contains the core non-strategic layers that future agents and training systems will build on:

- environment documentation,
- modular project architecture,
- static English card database,
- raw observation parser,
- typed action abstraction layer,
- factual game analysis API,
- replay and debug logging.

## Current Phase

Current completed phase: Phase 6 - Replay And Debug Logging

This phase adds a development-only replay system that records parsed board state, legal typed actions, chosen actions, and optional decision metadata in Markdown and JSON formats.

## Completed Phases

- Phase 0 - Environment Documentation
- Phase 1 - Project Architecture
- Phase 2 - English Card Database
- Phase 3 - Observation Parser
- Phase 4 - Action System
- Phase 5 - Game Analysis API
- Phase 6 - Replay And Debug Logging

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

- `poketcg.debug`
  Development-only replay capture, formatting, and replay file writing.

- `tests.cards`, `tests.engine`, `tests.actions`, `tests.analysis`, `tests.debug`
  Verification coverage for the currently implemented layers.

## Remaining Roadmap

- Agent-facing orchestration and submission boundary wiring.
- Rule-based baseline strategy layer.
- Search abstractions and MCTS.
- Encoding layer for model inputs and action representations.
- Reinforcement learning and self-play infrastructure.
- Evaluation and benchmarking systems.

## Not Yet Implemented

- gameplay logic,
- heuristics,
- policy selection,
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
- Debug logging reference: [docs/debug_logging.md](C:\Users\vipee\Desktop\study\project\poketcg\docs\debug_logging.md)
