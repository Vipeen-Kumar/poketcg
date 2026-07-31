# Replay And Debug Logging Reference

This document describes the development-only replay and debug logging system.

Its job is:

```text
Observation
     +
Typed Actions
     +
Optional Decision Metadata
        |
        v
ReplayLogger
        |
        v
ReplaySession
        |
        +--> Markdown replay
        `--> JSON replay
```

This module is the project's flight recorder.

It does not:

- choose actions,
- rank actions,
- score positions,
- modify `GameState`,
- mutate action objects,
- affect gameplay.

It only records what happened and why a future agent says it happened.

## Why This Module Exists

The project now has:

- parsed observations,
- typed actions,
- factual game analysis queries.

That is enough to make decisions later, but not enough to debug those decisions clearly.

We need a stable replay trail that can answer questions such as:

- what did the board look like,
- what legal actions existed,
- which action was chosen,
- what rule or policy chose it,
- what happened in recent turns,
- why some action was unavailable.

This package exists solely for that developer workflow.

## Package Layout

Main files:

- [src/poketcg/debug/models.py](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\debug\models.py)
- [src/poketcg/debug/replay_logger.py](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\debug\replay_logger.py)
- [src/poketcg/debug/replay_writer.py](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\debug\replay_writer.py)
- [src/poketcg/debug/formatter.py](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\debug\formatter.py)

## Core Models

### `ReplaySession`

Represents one complete game.

It stores:

- game id,
- start and finish timestamps,
- session status,
- replay metadata,
- ordered turn snapshots,
- output file paths after writing.

### `TurnSnapshot`

Represents one decision point.

It stores:

- turn number,
- current player,
- game phase,
- terminal result if present,
- perspective player snapshot,
- opponent snapshot,
- all legal typed actions,
- optional chosen action,
- optional decision metadata,
- log event names from the observation.

### `PlayerSnapshot`

Captures a serializable player summary:

- active Pokemon,
- bench Pokemon,
- prize count,
- deck count,
- hand count,
- discard count.

### `PokemonSnapshot`

Captures a serializable Pokemon summary:

- name,
- card id,
- current HP,
- max HP,
- damage taken,
- status conditions,
- attached energy types,
- attached energy count,
- tools.

### `ActionRecord`

Captures a human-readable and JSON-friendly description of one legal or chosen typed action.

Stored fields:

- action type,
- action index,
- human-readable description.

### `DecisionMetadata`

Reserved for future rule engines, baseline agents, search systems, and learned policies.

Stored fields:

- `rule_name`
- `reason`
- `confidence`
- `notes`

These may be empty in the current phase.

## Main API

### `ReplayLogger`

Construction:

```python
logger = ReplayLogger()
```

Main calls:

```python
logger.start_game(...)
logger.log_turn(...)
logger.log_action(...)
logger.finish(...)
```

### `start_game`

Creates a replay session for one game.

### `log_turn`

Captures a turn snapshot from:

- the parsed observation,
- typed legal actions,
- optional chosen action,
- optional decision metadata.

If no analyzer is supplied, it constructs a `GameAnalyzer` internally.

### `log_action`

Updates the most recent snapshot with the chosen action and optional decision metadata.

This is useful when the board snapshot and the final decision are recorded in separate steps.

### `finish`

Marks the replay finished and writes outputs through `ReplayWriter`.

## Output Formats

## Markdown

The Markdown format is intended for humans.

It includes:

- turn header,
- current player,
- phase,
- perspective board summary,
- opponent board summary,
- legal actions,
- chosen action,
- decision metadata,
- log event names.

Example structure:

```text
==================================================
Turn 4
==================================================

Current Player: SELF
Phase: MAIN

Me

Active:
Lillie's Cutiefly
HP 20/30
...

Legal Actions

1. End Turn
2. Attack #1: Hold Still
3. Play Card #2: Precious Trolley
```

## JSON

The JSON format is intended for tooling.

It serializes the full replay session so future code can build:

- replay viewers,
- dashboards,
- analytics jobs,
- evaluation artifacts.

The JSON output is derived only from the serializable replay models.

## Formatting Separation

Formatting is intentionally separate from replay capture.

`ReplayLogger` builds snapshots.

`ReplayWriter` writes files.

`MarkdownReplayFormatter` and `JsonReplayFormatter` own rendering.

This keeps responsibilities clean and avoids mixing presentation code into the logging flow.

## Output Location

Default output location:

- `outputs/replays/`

Example files:

- `outputs/replays/game_001.md`
- `outputs/replays/game_001.json`

These generated files are ignored in Git.

## Configuration

Replay logging is optional and designed to have negligible overhead when disabled.

Current configuration supports:

- enabled / disabled flag,
- output directory,
- Markdown output toggle,
- JSON output toggle,
- maximum saved games,
- reserved compression field for future extension.

Relevant config objects:

- `ReplayLoggingConfig` in [src/poketcg/config.py](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\config.py)
- `ReplayLoggerConfig` in [src/poketcg/debug/replay_logger.py](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\debug\replay_logger.py)

## Architecture Boundaries

This package depends on:

- parsed `Observation`,
- typed actions,
- `GameAnalyzer`,
- optional future decision metadata.

It does not sit underneath parser or action construction.

That matters because:

- parser remains the raw-environment adapter,
- actions remain the legal-option abstraction layer,
- analysis remains the factual query layer,
- debug remains the recording layer.

This separation prevents circular imports and keeps the replay system read-only.

## Performance

When disabled:

- `start_game()` returns immediately,
- `log_turn()` returns immediately,
- `log_action()` returns immediately,
- `finish()` returns immediately.

That keeps the runtime overhead negligible for normal gameplay or bulk training loops where replay capture is turned off.

## Tests

Current test coverage includes:

- replay creation,
- turn logging,
- Markdown formatting,
- JSON serialization,
- disabled logging behavior,
- empty turns,
- terminal games.

## Future Extension Points

Likely future additions:

- compression support for archived replay bundles,
- richer log formatting from parsed `GameLogEntry`,
- replay indexing by matchup or experiment id,
- sliding-window summaries across previous turns,
- replay visualization tools,
- integration with future rule-engine and MCTS decision metadata.

These can be added without changing gameplay code because this package only records data.
