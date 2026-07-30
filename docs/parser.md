# Observation Parser Reference

This document describes the Phase 3 observation parsing layer.

Its job is simple and strict:

```text
Raw Kaggle/cabt observation
        |
        v
ObservationParser
        |
        v
Typed internal Observation / GameState
```

The parser is a translation boundary. It never performs strategy, evaluation, search, or gameplay decisions.

## Why This Module Exists

The external simulator exposes nested raw dictionaries with environment-specific field names, enum encodings, and perspective-sensitive indices.

That format is not stable enough to use across the entire codebase.

The parser exists to:

- isolate the external observation schema,
- validate required structure,
- decode raw enum values,
- attach `CardData` metadata to every card reference,
- expose a perspective-aware internal model,
- keep future strategy, search, RL, and evaluation code free from raw dictionary handling.

This is the "compiler frontend" of the project.

## Main Classes

### `ObservationParser`

Location:
- [src/poketcg/engine/observation_parser.py](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\engine\observation_parser.py)

Why it exists:
- concrete adapter from raw Kaggle/cabt payloads to internal models.

Responsibilities:
- parse raw observations,
- validate required fields,
- decode documented enum ids,
- build internal `Observation`, `GameState`, `Player`, `Pokemon`, `Card`, `GameLogEntry`, `SelectPrompt`, and `OptionReference` objects,
- integrate with `CardDatabase`.

### Parser exceptions

Location:
- [src/poketcg/engine/exceptions.py](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\engine\exceptions.py)

Why they exist:
- keep parser failures precise and actionable.

Current parser-specific exceptions:

- `MissingObservationFieldError`
- `InvalidObservationEnumError`
- `CorruptedObservationError`
- `MissingObservationCardError`

## Object Relationships

```text
Observation
|- state: GameState | None
|  |- players: (Player, Player)
|  |  |- active: Pokemon | None
|  |  |- bench: Bench
|  |  |- hand / discard / prizes
|  |
|  |- stadium: Card | None
|  |- looking: tuple[Card | None, ...] | None
|
|- logs: tuple[GameLogEntry, ...]
`- selection: SelectPrompt | None
   |- effect_context
   `- options: tuple[OptionReference, ...]
```

Every parsed card reference is backed by `CardDatabase` metadata through the `Card` domain object.

## CardDatabase Integration

The parser never leaves raw card ids in parsed state.

Whenever a card appears in the observation:

- Pokemon body card,
- hand card,
- discard card,
- prize card,
- attached energy card,
- tool card,
- pre-evolution card,
- select context card,
- effect source card,
- legal option card,
- log card references,

the parser performs a `CardDatabase.get(card_id)` lookup and builds a typed internal `Card`.

That means downstream modules can rely on:

- `card.metadata`
- `card.name`
- `card.card_type`
- `card.pokemon_type`
- `card.stage`

without manually touching `CardDatabase`.

### Performance note

The parser keeps a parse-scoped card cache keyed by:

- `card_id`
- `serial`
- `player_index`

This avoids rebuilding identical `Card` references multiple times inside one observation.

## Perspective Handling

The raw environment provides `yourIndex`, plus a two-player `players` list.

The parser converts that into:

- `game.me`
- `game.opponent`

instead of forcing future code to remember raw indices.

### How it works

If `yourIndex == 0`:

- raw player `0` becomes `PlayerSide.SELF`
- raw player `1` becomes `PlayerSide.OPPONENT`

If `yourIndex == 1`:

- raw player `1` becomes `PlayerSide.SELF`
- raw player `0` becomes `PlayerSide.OPPONENT`

This transformation is applied consistently for:

- `GameState.players`
- `game.me`
- `game.opponent`
- card ownership fields
- option ownership fields
- log player references

## Parsing Pipeline

### Step 1: Observation shell

The parser validates the top-level observation fields:

- `logs`
- `current`
- `select`

`current` and `select` may both be `None` during the initial deck-selection phase.

### Step 2: Game state

If `current` is present, the parser builds:

- turn metadata,
- perspective player index,
- first-player metadata,
- terminal result metadata,
- players,
- stadium,
- looking/revealed card references.

### Step 3: Players

Each player becomes a typed `Player` containing:

- `active`
- `bench`
- `hand`
- `hand_count`
- `deck_count`
- `discard`
- `prizes`
- `status_conditions`

### Step 4: Pokemon

Each Pokemon becomes a typed `Pokemon` containing:

- body card reference,
- current HP,
- max HP,
- `appeared_this_turn`,
- effective energy types,
- attached energy card references,
- attached tool card references,
- pre-evolution card references.

### Step 5: Logs

Every log entry becomes a typed `GameLogEntry`.

The parser:

- decodes log type,
- parses known documented fields,
- attaches cards where possible,
- preserves unknown extra fields in `metadata`.

The parser does not interpret log meaning beyond structural parsing.

### Step 6: Legal selection

If `select` is present, the parser builds:

- `SelectPrompt`
- `EffectContext`
- `OptionReference` entries

Preserved fields include:

- selection type,
- selection context,
- min/max count,
- effect source card,
- context card,
- exposed deck cards,
- remaining damage counters,
- remaining energy cost,
- option details.

## Validation Rules

The parser validates:

- required top-level fields,
- required player fields,
- exactly two players,
- active list length `0..1`,
- integer fields that must be integers,
- boolean fields that must be booleans,
- documented enum values,
- referenced card ids that must exist in `CardDatabase`.

Unknown extra fields are ignored gracefully and may be preserved in metadata for logs/options.

## Enum Decoding

The parser supports documented raw enum ids from `cabt` for:

- zones,
- Pokemon types,
- select types,
- select contexts,
- option types,
- status conditions,
- log types.

It also accepts string enum names when present.

This makes the parser more robust to small serialization differences between SDK surfaces.

## Error Handling

### `MissingObservationFieldError`

Used when a required field is absent.

Example:
- `observation.current.players` missing

### `InvalidObservationEnumError`

Used when an enum value is unknown.

Example:
- unknown `OptionType`
- unknown `SelectContext`

### `CorruptedObservationError`

Used when the observation shape is internally invalid.

Example:
- non-list where a list is required
- active slot list longer than one
- malformed integer field

### `MissingObservationCardError`

Used when the observation references a card id not present in `CardDatabase`.

## Convenience Properties

The domain layer exposes convenience accessors so downstream modules stay clean:

- `observation.turn`
- `observation.me`
- `observation.opponent`
- `observation.result`
- `observation.is_terminal`
- `observation.energy_attached`
- `observation.supporter_played`
- `observation.retreated`
- `state.me`
- `state.opponent`
- `state.is_terminal`

These are view conveniences only. They do not make decisions.

## Assumptions

The parser currently assumes:

1. Observations represent exactly two players.
2. The environment uses the documented `cabt` field names.
3. `CardDatabase` is already loaded before parser use.
4. Raw enum values are either documented integers or enum-name strings.
5. The parser should preserve structure, not infer hidden gameplay semantics.

## Future Extension Points

Safe future extensions include:

- richer log-field typing if more official log schemas become available,
- replay-file parsing reusing the same internal builders,
- lightweight parse metrics / instrumentation,
- structured serialization of parsed observations,
- parser adapters for alternate simulator wrappers if Kaggle runtime formatting changes.

These can be added without changing downstream strategy/search/training code, which is the whole point of this layer.
