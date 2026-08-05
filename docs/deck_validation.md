# Deck Validation

This document describes the Phase 11 deck legality subsystem.

## Purpose

The deck validator exists to catch illegal decks before the official `cabt` SDK sees them.

It is responsible for:

- loading `deck.csv`,
- validating the deck size,
- validating copy limits,
- validating ACE SPEC limits,
- reporting descriptive validation failures,
- staying extensible for future deck legality rules.

It does not:

- build a strategy deck,
- score cards,
- evaluate gameplay,
- talk to the Kaggle environment.

## Package Layout

```text
src/poketcg/deck/
    __init__.py
    models.py
    validator.py
    rules.py
    loader.py
    exceptions.py
```

## Architecture

### `DeckLoader`

`DeckLoader` reads a deck file from disk, converts it into a typed `Deck`, and validates it immediately.

That gives us one simple rule:

```text
No invalid deck should reach BattleStart.
```

### `DeckValidator`

`DeckValidator` applies a list of reusable rules to a `Deck`.

The current rule order is:

1. unknown card ids,
2. deck size,
3. ACE SPEC limit,
4. normal copy limit.

This order makes the failure messages easier to understand.

### Rules

Each rule is intentionally small and composable.

Current rules:

- `UnknownCardRule`
- `DeckSizeRule`
- `AceSpecLimitRule`
- `DeckCopyLimitRule`

The rules use `CardDatabase` as their source of truth.

## ACE SPEC Detection

ACE SPEC detection is derived from card metadata.

The current implementation uses the `CardData.is_ace_spec()` helper, which checks normalized card metadata rather than hardcoding a specific card id.

That keeps the validator stable even if future card sets add or rename ACE SPEC cards.

## Validation Errors

Validation failures raise descriptive exceptions from `src/poketcg/deck/exceptions.py`.

Example:

```text
Deck validation failed:
- ACE SPEC card "Unfair Stamp" may appear only once. Card ID: 1080. Copies found: 4. Maximum allowed: 1.
```

## Integration Points

The deck validator is used by:

- `BaselineAgent` startup,
- `run_local.py`,
- `build_submission.py`,
- `deck.csv` loading.

## Future Extensions

Likely future rules:

- format-specific legality,
- set restrictions,
- custom tournament constraints,
- banned-list support,
- deck archetype metadata.
