# Decision Engine Reference

This document describes the deterministic decision engine introduced in Phase 6.

Its job is:

```text
DecisionContext
       |
       v
DecisionEngine
       |
       +--> registered rules in priority order
       |
       +--> serializable rule results and decision trace
       |
       `--> safe fallback action when no rule succeeds
```

The decision engine is intentionally narrow.

It does not:

- parse raw observations,
- build legal actions,
- choose search branches,
- score board positions,
- run Monte Carlo Tree Search,
- train policies,
- infer hidden information beyond the parsed state.

The Pokémon-specific rule implementations live in [docs/rules.md](C:\Users\vipee\Desktop\study\project\poketcg\docs\rules.md) and the [src/poketcg/rules](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\rules) package.

## Responsibilities

The decision engine owns how a typed action is selected from a legal action set.

That means it is responsible for:

- loading registered rules,
- sorting rules by priority,
- evaluating one rule at a time,
- stopping at the first successful rule,
- returning one typed action,
- recording a trace for every rule that was actually evaluated,
- falling back to a safe deterministic action if no rule succeeds.

It is not responsible for strategic knowledge.

Phase 7 and later layers can add actual Pokémon strategy on top of this engine by introducing more specific rules.

## Main Objects

### `DecisionContext`

Location:
- [src/poketcg/decision/context.py](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\decision\context.py)

Why it exists:
- bundles the parsed state, analyzer, legal actions, configuration, and optional replay logger into one object.

Stored data:
- `game_state`
- `analyzer`
- `legal_actions`
- `config`
- `replay_logger`
- `metadata`

The context keeps the engine from needing long parameter lists and gives future extensions one stable place to attach extra decision metadata.

### `DecisionEngine`

Location:
- [src/poketcg/decision/engine.py](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\decision\engine.py)

Main call:

```python
action = decision_engine.choose_action(context)
```

This method returns one typed action and never returns `None`.

The engine also exposes `decide(context)` for callers that want the action plus the full decision trace.

### `BaseRule`

Rules are deterministic, reusable units of behavior.

Required surface:

- `name`
- `priority`
- `enabled`
- `applies(context)`
- `evaluate(context)`

Rules should not parse raw observations or construct their own legal action lists.

They receive a `DecisionContext` and return a `RuleResult`.

## Rule Lifecycle

1. A rule class is imported.
2. The rule auto-registers with the shared registry.
3. The engine loads registered rules.
4. The registry filters disabled rules and orders the rest by priority.
5. The engine evaluates each rule in order.
6. The first passing rule wins.
7. If no rule passes, the fallback rule chooses a safe legal action.

The engine never instantiates rules manually one by one.

Applications typically import `poketcg.rules` once during startup so the built-in Pokémon rule library registers itself before the first decision.

## Rule Results

`RuleResult` is the serializable record of one rule evaluation.

Fields:

- `rule_name`
- `passed`
- `selected_action`
- `reason`
- `priority`
- `metadata`
- `execution_time`

The object is kept serializable so the replay logger, debug tooling, and future analytics can reuse the same trace without reformatting the result by hand.

## Decision Trace

The engine records every rule it actually evaluated.

Example shape:

```text
Rule: AlwaysEndTurnRule
Result: FAILED
Reason: End turn is unavailable.

Rule: FirstLegalActionRule
Result: PASSED
Reason: Selected the first legal action.
```

The trace is serializable and can be consumed directly by the replay logger.

## Registry

### `RuleRegistry`

Location:
- [src/poketcg/decision/registry.py](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\decision\registry.py)

Responsibilities:

- own every rule instance,
- prevent duplicate names,
- enable and disable rules,
- return the fallback rule,
- load plugin modules,
- expose ordered rules for the engine.

The registry is the ownership boundary for rules.

The engine asks for ordered rules; it does not manually build the set itself.

## Rule Ordering

Rules are ordered by a deterministic priority resolver.

Current ordering behavior:

- higher numeric priority runs first,
- dependency edges in `runs_before` and `runs_after` are respected,
- equal-priority rules are ordered deterministically,
- cycles raise a configuration error.

This gives later plugin rules a stable way to enforce relative ordering without hardcoding rule lists into the engine.

## Fallback Policy

The fallback policy exists to guarantee a safe choice even when no higher-priority rule succeeds.

Priority:

1. End Turn, if legal.
2. Otherwise, the first legal action.

This fallback exists because production code must never return `None`, and a deterministic engine still needs a final legal choice when no specialized rule applies.

## Replay Integration

The replay logger can consume the decision trace directly.

That means a caller can record:

- the legal actions that existed,
- the action that was chosen,
- the rule trace that led to the choice,
- the human-readable reason for the winning rule.

This keeps debug output aligned with the actual decision path instead of reconstructing it later.

## Configuration

Decision configuration currently supports:

- `enabled_rules`
- `disabled_rules`
- `priority_overrides`
- `strict_mode`
- `logging_enabled`
- `plugin_modules`

Strict mode is meant to surface bad configuration early rather than letting subtle rule-loading mistakes leak into gameplay.

## Extension Points

Likely future additions:

- later strategic rules,
- Pokémon-specific heuristics,
- richer plugin loading for external rule packs,
- more detailed trace summaries,
- agent-facing orchestration on top of the engine,
- rule-specific telemetry for benchmarking.

The key architectural constraint is unchanged:

the decision engine executes rules; it does not own strategy.