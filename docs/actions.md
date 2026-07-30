# Action System Reference

This document describes the typed action abstraction layer built on top of the observation parser.

Its job is:

```text
Parsed SelectPrompt / OptionReference
        |
        v
ActionFactory
        |
        v
Typed BaseAction subclasses
```

This layer is the AST stage after parsing.

It does not decide:

- whether an action is good,
- whether an action is legal,
- whether a move should be preferred,
- whether a retreat is smart,
- whether an attack is worth using.

It only classifies already-legal parsed options into strongly typed action objects.

## Why This Module Exists

The observation parser already removes raw Kaggle dictionaries.

However, downstream modules still should not need to inspect:

- `option.option_type`,
- zone/index combinations,
- raw selection layouts,
- action-specific metadata placement.

The action layer exists so future code can ask for:

- `AttackAction`
- `PlayCardAction`
- `RetreatAction`
- `ChoiceAction`

instead of manually switching on parsed option types.

## Package Layout

Main files:

- [src/poketcg/actions/models.py](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\actions\models.py)
- [src/poketcg/actions/factory.py](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\actions\factory.py)
- [src/poketcg/actions/enums.py](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\actions\enums.py)
- [src/poketcg/actions/exceptions.py](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\actions\exceptions.py)

## Action Hierarchy

### `BaseAction`

Common fields:

- `action_index`
- `kind`
- `option`
- `selection_context`
- `selection_type`
- `metadata`

Most importantly, `action_index` preserves the exact legal option index from the selection prompt so an agent can return it directly to Kaggle later.

### Main concrete actions

- `PlayCardAction`
- `AttachEnergyAction`
- `EvolutionAction`
- `AbilityAction`
- `RetreatAction`
- `AttackAction`
- `EndTurnAction`
- `ChoiceAction`
- `CardChoiceAction`
- `EnergyChoiceAction`
- `SpecialConditionChoiceAction`
- `UnknownAction`

## Factory Design

### `ActionFactory`

Public entry points:

- `from_selection(selection, state=None)`
- `from_observation(observation)`

`from_observation()` is the most ergonomic API because it can use both:

- parsed selection data,
- parsed state data

to enrich actions.

### Why the factory exists

Without a factory, every future strategy or search module would need to repeat option-type branching.

Centralizing the conversion gives us:

- one mapping from option type to action class,
- one validation point,
- one place to preserve compatibility when the simulator evolves.

## Relationship with the Parser

The parser and action system are intentionally separate.

### Parser responsibilities

- raw payload validation,
- enum decoding,
- card metadata resolution,
- perspective transformation,
- typed state and typed options.

### Action-system responsibilities

- interpret typed options as typed actions,
- preserve option index,
- expose action-specific convenience fields.

That boundary matters because the parser is a schema translator, while the action layer is a semantic classification layer.

## CardDatabase Integration

The action layer does not talk to the CSV directly.

It benefits from `CardDatabase` through the parser:

- `OptionReference.card` is already a typed `Card`,
- `Pokemon.card.metadata` is already a typed `CardData`.

That allows the factory to expose richer typed fields without performing fresh CSV parsing.

## Attack Metadata Handling

Attack options carry an `attack_id`, but the current static metadata system does not own official simulator attack-id mappings.

So the factory uses safe best-effort enrichment:

- if the number of attack options matches the number of static attacks on the active Pokemon, it aligns them by order,
- if there is exactly one static attack and one attack option, it uses that attack,
- otherwise it still produces an `AttackAction`, but some enriched fields may remain `None`.

This keeps the layer useful without making undocumented assumptions.

## Validation Rules

The action factory validates action-specific structure.

Examples:

- `PlayCardAction` requires a card reference,
- malformed selections raise action-layer exceptions,
- unsupported option types fall back to `UnknownAction` instead of silently breaking downstream modules.

Current action-layer exceptions:

- `ActionFactoryError`
- `ActionValidationError`
- `CorruptedActionError`

## Hidden Environment Details

Future modules should not switch on raw environment option ids.

This layer hides:

- raw option-type integers,
- raw Kaggle selection branching patterns,
- zone/index wiring details where a typed action can expose a clearer field.

That is one of the main reasons this package exists.

## Future Extension Points

Likely future extensions:

- more precise ability-source resolution,
- more precise attack-id-to-attack metadata mapping,
- explicit target abstractions for multi-target or nested selections,
- serializer helpers for action traces,
- submission-time action selection adapters built on top of `action_index`.

These can be added without changing the parser contract or forcing downstream modules to read raw option shapes again.
