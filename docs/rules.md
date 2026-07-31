# Rule Library Reference

This document describes the Pokémon knowledge layer introduced in Phase 8.

Its job is:

```text
DecisionContext
      |
      v
Pokémon rule library
      |
      v
deterministic gameplay rule result
      |
      v
DecisionEngine selects one typed action
```

The rule library owns the Pokémon-specific part of decision making.

It does not:

- parse raw observations,
- build legal actions,
- execute fallback orchestration itself,
- run search or learning systems,
- score positions,
- estimate future value.

## Responsibilities

Each rule answers one question.

Examples:

- `AttackRule`: should I attack?
- `RetreatRule`: should I retreat?
- `AttachEnergyRule`: should I attach energy?
- `EvolutionRule`: should I evolve?
- `SupporterRule`: should I play a supporter?
- `ItemRule`: should I play an item?
- `AbilityRule`: should I use an ability?
- `StadiumRule`: should I play a stadium?
- `EndTurnRule`: should I end the turn?
- `FallbackRule`: what is the safest legal action when nothing else applies?

Rules stay deliberately small and deterministic.

## Main Objects

### `BaseRule`

Location:
- [src/poketcg/rules/base.py](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\rules\base.py)

Common surface:

- `name`
- `description`
- `priority`
- `enabled`
- `applies(context)`
- `evaluate(context)`

`BaseRule` extends the generic decision-engine rule interface and adds a human-readable description field.

### Rule modules

Each rule has its own module under [src/poketcg/rules](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\rules).

Current modules:

- `attack.py`
- `energy.py`
- `retreat.py`
- `evolution.py`
- `supporter.py`
- `item.py`
- `ability.py`
- `stadium.py`
- `end_turn.py`
- `fallback.py`

## Rule Lifecycle

1. A rule module is imported.
2. The rule class is defined.
3. The generic decision-engine base auto-registers the rule instance.
4. The Decision Engine reads registered rules from the shared registry.
5. The rule either passes with one selected action or fails with a reason.

The rule library does not instantiate rules manually during decision time.

## Decision Engine Integration

The generic Decision Engine remains in [docs/decision_engine.md](C:\Users\vipee\Desktop\study\project\poketcg\docs\decision_engine.md).

It simply executes registered rules in priority order and returns the first successful action.

This means the rule library owns the gameplay knowledge, while the engine owns the deterministic execution mechanism.

## Rule Ordering

Rules are ordered by priority.

Default priorities are intentionally simple and deterministic.

The registry also supports:

- enable/disable toggles,
- priority overrides,
- plugin-loaded modules.

## Rule Results

Rules return the existing serializable `RuleResult` model from the decision package.

Each result includes:

- rule name,
- pass/fail state,
- selected action,
- reason,
- priority,
- metadata,
- execution time.

That keeps replay logging and future analytics consistent.

## How To Add A Rule

1. Pick the single gameplay question the rule should answer.
2. Add a new module under [src/poketcg/rules](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\rules).
3. Subclass `rules.base.BaseRule`.
4. Implement `applies(context)` and `evaluate(context)`.
5. Keep the rule deterministic and small.
6. Add unit tests for both success and failure cases.

## Example

```python
from poketcg.rules import AttackRule

rule = AttackRule()
if rule.applies(context):
    result = rule.evaluate(context)
    if result.passed:
        action = result.selected_action
```

## Extension Points

Likely future additions:

- deck-specific rule bundles,
- aggressive and defensive rule packs,
- control-style rules,
- plugin-loaded third-party rules,
- richer rule metadata and tags,
- conditional rule enablement.

The core guarantee stays the same:

the rule library owns Pokémon knowledge, and the decision engine just executes it.