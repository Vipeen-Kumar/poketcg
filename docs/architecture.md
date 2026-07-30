# Architecture Reference

This document explains the software architecture decisions for the `poketcg` project.

The environment contract and terminology come from [environment.md](C:\Users\vipee\Desktop\study\project\poketcg\docs\environment.md), which remains the source of truth for simulator behavior.

## Design Principles

- Single responsibility per package.
- Clear separation between domain models and environment-specific adapters.
- Low coupling between decision logic, search, training, and infrastructure.
- Composition over inheritance.
- Strong typing from the start.
- Kaggle submission concerns isolated from the larger development codebase.

## Top-Level Layout

### `docs/`

Why it exists:
- Holds long-form project documentation.

Why it is separated:
- Architecture and environment semantics should be readable without importing code.

Future phases:
- used by every phase for onboarding, design decisions, and contributor guidance.

### `data/`

Why it exists:
- Dedicated location for static inputs and future generated artifacts.

Why it is separated:
- Keeps raw card data and future processed datasets out of source packages.

Future phases:
- card metadata ingestion,
- replay exports,
- offline training datasets,
- evaluation artifacts.

### `src/poketcg/`

Why it exists:
- Main Python package using a `src/` layout.

Why it is separated:
- Prevents accidental imports from the project root and keeps packaging cleaner for large codebases.

Future phases:
- all core software modules.

### `tests/`

Why it exists:
- Mirrors source packages for unit, integration, and future regression tests.

Why it is separated:
- Keeps test code independent from runtime code and scales well for a 30k+ LOC project.

Future phases:
- parser tests,
- state-model tests,
- search tests,
- training pipeline tests,
- submission smoke tests.

## Package Responsibilities

### `poketcg.domain`

Why it exists:
- Canonical domain model of cards, state, actions, observations, and related enums.

Why it is separated:
- The rest of the project should depend on stable internal models, not raw Kaggle dictionaries.

Future phases:
- all phases consume the domain layer.

### `poketcg.cards`

Why it exists:
- Owns card metadata concerns only.

Why it is separated:
- Static catalog data should not be mixed with dynamic battle-state parsing.

Future phases:
- metadata loading,
- card indexing,
- feature lookup,
- deck validation support.

### `poketcg.engine`

Why it exists:
- Boundary around environment-facing adapters and observation/action translation.

Why it is separated:
- Kaggle/cabt specifics should not leak through the whole codebase.

Future phases:
- observation parsing,
- legal action translation,
- local simulator integration,
- replay ingestion.

### `poketcg.agent`

Why it exists:
- Home for the high-level agent contract and submission-facing orchestration.

Why it is separated:
- The final Kaggle entrypoint should remain thin and delegate to composable internals.

Future phases:
- competition runtime wrapper,
- self-play agent wrappers,
- evaluation agent harnesses.

### `poketcg.strategy`

Why it exists:
- Strategy selection boundary independent of concrete algorithms.

Why it is separated:
- Rule-based logic, policy-based logic, and search-based logic should share an interface without depending on each other.

Future phases:
- rule-based policy,
- hybrid policy/search orchestration.

### `poketcg.search`

Why it exists:
- Dedicated search abstractions and later implementations.

Why it is separated:
- Search code tends to grow quickly and should not contaminate policy or environment modules.

Future phases:
- MCTS,
- rollout planning,
- search diagnostics.

### `poketcg.rl`

Why it exists:
- Reinforcement-learning-specific abstractions.

Why it is separated:
- Training systems, replay buffers, learners, and rollout collection should stay isolated from inference-time agent code.

Future phases:
- self-play loops,
- learners,
- replay storage,
- curriculum logic.

### `poketcg.encoding`

Why it exists:
- Boundary for state/action encoding and future tensor preparation.

Why it is separated:
- Feature encoding changes often and should not be embedded in policy or parser code.

Future phases:
- observation encoders,
- action encoders,
- model input pipelines.

### `poketcg.evaluation`

Why it exists:
- Evaluation and benchmarking interfaces.

Why it is separated:
- Offline evaluation, matchup benchmarking, and tournament harnesses are distinct from training and inference.

Future phases:
- matchup runners,
- score reports,
- regression benchmarks.

### `poketcg.training`

Why it exists:
- Generic training orchestration boundary independent of RL specifics.

Why it is separated:
- Training workflows may later include imitation, supervised warm starts, and RL.

Future phases:
- training runners,
- experiment coordination,
- checkpoints and run metadata.

### `poketcg.shared`

Why it exists:
- Shared cross-cutting runtime concerns.

Why it is separated:
- Exceptions and logging should be reusable without creating circular dependencies.

Future phases:
- used by every package.

### `poketcg.utils`

Why it exists:
- Small reusable helper modules with no domain ownership.

Why it is separated:
- Prevents helper code from leaking into unrelated packages.

Future phases:
- serialization,
- file handling,
- timing,
- validation support.

## Why a Domain Core?

The environment reference shows that the simulator exposes:

- observations,
- logs,
- current state,
- legal options,
- hidden-information boundaries.

Those concepts are long-lived and central. A dedicated domain core makes future code easier to test and easier to adapt if the external environment format changes.

## Why Separate `engine` from `domain`?

Because the raw environment is an external API boundary. The project should be able to:

- parse raw `cabt` observations into internal models,
- test internal models without simulator dependencies,
- swap parser implementations without touching strategies or trainers.

## Why Separate `strategy`, `search`, `rl`, and `encoding`?

These concerns evolve at different speeds:

- strategy defines how choices are made,
- search defines how futures are explored,
- RL defines how policies are trained,
- encoding defines how data is represented for models.

Keeping them separate reduces refactor pressure when one subsystem changes.

## Why a Thin Agent Layer?

The Kaggle runtime contract is small, but the internal project will become large. A thin `agent` package keeps the submission boundary simple while allowing the real system to grow behind it.
