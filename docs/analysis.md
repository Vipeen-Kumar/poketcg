# Game Analysis Reference

This document describes the Phase 5 game analysis layer.

Its job is:

```text
Parsed Observation
     +
Typed Action Batch
        |
        v
GameAnalyzer
        |
        v
Reusable factual queries
```

The analysis layer is intentionally read-only.

It does not:

- choose actions,
- score positions,
- rank legal moves,
- evaluate trades,
- run search,
- learn policies.

It only answers factual questions about the current parsed observation.

## Why This Module Exists

By Phase 4, the project already had:

- a typed card metadata system,
- a typed observation parser,
- a typed action abstraction layer.

However, future modules would still be forced to repeat the same board-inspection logic:

- count energy,
- count prizes,
- inspect bench space,
- test for visible Supporters or Items,
- filter legal actions by type,
- check status conditions,
- enumerate attacks,
- calculate damage already on a Pokemon.

This package exists so that repeated factual queries live in one place.

Think of it as a query layer over `Observation`, `GameState`, and typed actions.

## Main Class

### `GameAnalyzer`

Location:
- [src/poketcg/analysis/analyzer.py](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\analysis\analyzer.py)

Construction:

```python
analyzer = GameAnalyzer(observation)
```

Optional prebuilt actions can also be injected:

```python
action_batch = ActionFactory().from_observation(observation)
analyzer = GameAnalyzer(observation, actions=action_batch)
```

This is useful when future code already built typed actions and wants to avoid recomputing them.

## Responsibilities

The analysis package is responsible for:

- exposing factual convenience queries over parsed state,
- exposing factual convenience queries over typed legal actions,
- centralizing common counters and selectors,
- avoiding repeated manual inspection of `GameState`,
- adding lightweight lazy caching for reused aggregates.

It is not responsible for:

- deciding whether a fact is strategically good or bad,
- transforming observations from raw payloads,
- constructing raw Kaggle selections,
- inferring hidden information beyond what is already parsed,
- enforcing rules or legality.

## Relationship to Other Layers

### Parser

The parser owns:

- raw schema validation,
- enum decoding,
- card resolution,
- perspective handling,
- typed state construction.

The analyzer assumes parsing is already complete.

### Actions

The action layer owns:

- converting legal options into typed action objects,
- preserving Kaggle option indices,
- action-specific structural enrichment.

The analyzer reuses that layer to answer questions such as:

- what attack actions exist,
- whether retreat is currently legal,
- whether an end-turn action exists,
- how many play or evolution actions are available.

### Strategy / Search / RL

Future decision-making systems should consume this layer, not re-implement routine factual queries.

That keeps strategy code smaller and makes later refactors safer.

## Available Query Families

## Game-Level Queries

Examples:

- `is_terminal()`
- `current_turn()`
- `current_player()`
- `first_player()`

These answer match-level state questions only.

## Player Queries

Examples:

- `me()`
- `opponent()`
- `active()`
- `bench()`
- `hand()`
- `deck_size()`
- `discard()`
- `prizes_remaining()`
- `bench_space()`
- `has_empty_bench_slot()`

These provide perspective-aware accessors and basic board counts.

## Pokemon Queries

Examples:

- `can_attack()`
- `can_retreat()`
- `can_evolve()`
- `damage_taken()`
- `hp_remaining()`
- `has_energy()`
- `energy_count()`
- `has_tool()`
- `is_knocked_out()`
- `has_status_condition()`

These methods return facts only.

For example, `can_attack()` means:

- the current legal action set contains an attack action relevant to the current active Pokemon.

It does not mean:

- attacking is a good idea.

## Attack Queries

Examples:

- `available_attacks()`
- `attack_cost()`
- `attack_damage()`
- `attack_names()`
- `attack_count()`

These are read from static card metadata attached by the parser.

They do not attempt to solve undocumented simulator attack-id mappings beyond what already exists in the action layer.

## Card / Hand Queries

Examples:

- `has_supporter()`
- `has_item()`
- `has_stadium()`
- `has_tool()`
- `basic_pokemon_in_hand()`
- `energy_cards_in_hand()`
- `search_cards()`

These are intentionally visible-information queries.

If the opponent hand is hidden, these methods return facts about the visible parsed representation, not guessed cards.

## Board Queries

Examples:

- `active_pokemon()`
- `bench_pokemon()`
- `total_energy()`
- `total_hp()`
- `total_damage()`
- `total_prizes()`

By default these operate from the perspective player's board unless another player/side is passed.

## Legal Action Queries

Examples:

- `actions()`
- `attack_actions()`
- `retreat_actions()`
- `energy_actions()`
- `play_actions()`
- `end_turn_action()`
- `evolution_actions()`
- `ability_actions()`

These are built from the typed action layer, not by reading raw option types directly.

## Status Queries

Examples:

- `is_poisoned()`
- `is_asleep()`
- `is_paralyzed()`
- `has_special_condition()`

These use the parsed status-condition fields and stay purely descriptive.

## Counter Queries

Examples:

- `pokemon_count()`
- `energy_count()`
- `tool_count()`
- `supporter_count()`
- `trainer_count()`

These are useful for rule engines, replay tooling, evaluation harnesses, and future encoders.

## Caching Design

The caching strategy is intentionally light.

The analyzer caches only small derived values that are likely to be reused:

- in-play Pokemon tuples per side,
- filtered action tuples by action class.

The cache is local to one `GameAnalyzer` instance.

There is no global cache and no mutable cross-observation state.

That keeps the layer simple and safe for per-decision reconstruction.

## Examples

### Example 1: Board inspection

```python
analyzer = GameAnalyzer(observation)

my_active = analyzer.active()
my_bench = analyzer.bench_pokemon()
damage_on_active = analyzer.damage_taken()
remaining_prizes = analyzer.prizes_remaining()
```

### Example 2: Hand queries

```python
if analyzer.has_supporter():
    supporters = analyzer.search_cards("supporter")
```

### Example 3: Legal action queries

```python
attack_actions = analyzer.attack_actions()
end_action = analyzer.end_turn_action()
```

These calls still do not decide what to do. They only expose structure.

## Edge Cases Handled

The current implementation is designed to behave safely for:

- setup observations with no state,
- observations with no legal selection,
- empty benches,
- missing active Pokemon,
- hidden opponent hand contents,
- terminal observations,
- injected prebuilt action batches.

## Future Extension Points

Likely safe future additions:

- log-analysis helpers built over parsed `GameLogEntry`,
- replay-window analysis spanning multiple observations,
- additional grouped queries for discard, prizes, and revealed cards,
- explicit opponent/public-information query helpers,
- encoder-facing batch extraction utilities that still remain factual.

These can be added without changing parser responsibilities or leaking heuristics into this package.
