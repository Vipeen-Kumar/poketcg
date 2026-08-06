# Rule Library Reference

This document describes the Pokémon knowledge layer introduced in Phase 8 and upgraded in Phase 12.

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

## Rule Hierarchy and Priorities

Rules are executed in priority order. The current tactical upgrade (Phase 12) introduced three high-priority rules for winning scenarios and improved several existing rules to be more strategic.

### Tactical Rules (High Priority - Handle Winning Conditions)

These rules prioritize immediate winning opportunities:

- **WinningAttackRule** (priority 1200): Select a lethal attack when it takes the final Prize cards.
  - `Applies when`: opponent has 1 Prize card remaining AND a lethal attack exists
  - `Behavior`: selects the attack that best KOs the opponent

- **KnockoutRule** (priority 1100): Prefer attacks that Knock Out the opponent's Active Pokémon.
  - `Applies when`: a lethal attack exists
  - `Behavior`: minimizes overkill damage, prefers efficient knockouts

- **AttachEnergyRule** (priority 1000): Attach energy to Pokémon closest to attacking.
  - `Applies when`: energy not yet attached this turn AND attachment would close an attack gap
  - `Behavior`: prioritizes reducing the energy cost gap for the Active Pokémon

### Strategic Rules (Medium Priority - Improve Board State)

These rules improve the overall game position:

- **EvolutionRule** (priority 900): Evolve when it clearly improves board state, survivability, or attack access.
  - `Applies when`: evolution available AND it provides HP/attack gain
  - `Behavior`: prioritizes HP gain, then attack potential, then energy investment

- **SupporterRule** (priority 800): Use supportive draw/search supporters only when beneficial.
  - `Applies when`: supporter not yet played this turn AND supporter looks beneficial (draw/search)
  - `Behavior`: selects supporter by score (matching keywords), then text length

- **RetreatRule** (priority 700): Retreat only if the new Active Pokémon materially improves the position.
  - `Applies when`: retreat possible AND bench Pokémon has better board value
  - `Behavior`: prioritizes HP, then attack potential, then energy state

- **PrizeRule** (priority 600): Prefer actions that improve Prize progression.
  - `Applies when`: a damaging attack exists
  - `Behavior`: selects highest-damage attack from non-lethal options

### Generic Rules (Lower Priority - Fallbacks)

These rules handle card play when tactical rules don't apply:

- **AttackRule** (priority 500): Select a legal attack when the active Pokémon can attack.
  - `Applies when`: can attack AND not asleep/paralyzed
  - `Behavior`: selects by attack priority score (lethal > damage > overkill > cost)

- **ItemRule** (priority 500): Select a legal Item play when one is available.
  - `Applies when`: item card in hand
  - `Behavior`: selects first available

- **AbilityRule** (priority 450): Select a legal ability action when one is available.
  - `Applies when`: ability playable
  - `Behavior`: selects first available

- **StadiumRule** (priority 400): Select a legal Stadium play when one is available.
  - `Applies when`: stadium not yet played this turn AND stadium in hand
  - `Behavior`: selects first available

- **EndTurnRule** (priority 100): Select the legal end-turn action when it exists.
  - `Applies when`: end-turn action is legal
  - `Behavior`: always selects end-turn

### Safety Rule (Fallback - Guarantees Legal Move)

- **FallbackRule** (priority -1000, is_fallback=True): Safety rule that always returns a legal action.
  - `Behavior`: prefers end-turn, otherwise selects first legal action
  - `Always runs last` when all other rules fail

## Responsibilities

Each rule answers one focused question and remains deterministic.

Examples:

- `WinningAttackRule`: can I win this turn by attacking?
- `KnockoutRule`: can I knock out the opponent's active?
- `RetreatRule`: should I retreat to a better Pokémon?
- `AttachEnergyRule`: should I attach energy toward an attack?
- `EvolutionRule`: should I evolve to improve my position?
- `SupporterRule`: should I play a beneficial supporter?
- `ItemRule`: should I play an item?
- `AbilityRule`: should I use an ability?
- `StadiumRule`: should I play a stadium?
- `EndTurnRule`: should I end my turn?
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

- `winning_attack.py` - tactical: handle final prize situations
- `knockout.py` - tactical: prefer knockout attacks
- `prize.py` - strategic: improve prize progression
- `attack.py` - generic: select any attack
- `energy.py` - strategic: attach energy toward attacks
- `retreat.py` - strategic: retreat to better pokémon
- `evolution.py` - strategic: evolve when beneficial
- `supporter.py` - strategic: play beneficial supporters
- `item.py` - generic: play items
- `ability.py` - generic: use abilities
- `stadium.py` - generic: play stadiums
- `end_turn.py` - generic: end the turn
- `fallback.py` - safety: always selects a legal action
- `strategy.py` - shared helpers for heuristics

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
- reason (informative explanation of the decision),
- priority,
- metadata,
- execution time.

That keeps replay logging and future analytics consistent.

## How To Add A Rule

1. Pick the single gameplay question the rule should answer.
2. Add a new module under [src/poketcg/rules](C:\Users\vipee\Desktop\study\project\poketcg\src\poketcg\rules).
3. Subclass `rules.base.BaseRule`.
4. Implement `applies(context)` and `evaluate(context)`.
5. Set appropriate `default_priority` (higher = runs sooner).
6. Keep the rule deterministic and small.
7. Add unit tests for both success and failure cases.
8. Import in `rules/__init__.py` to trigger auto-registration.

## Example

```python
from poketcg.rules import WinningAttackRule

rule = WinningAttackRule()
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

## Phase 12 Changes

Upgraded from Phase 8 baseline agent to Phase 12 tactical rule-based strategy:

- Added three high-priority tactical rules (WinningAttackRule, KnockoutRule, PrizeRule)
- Improved AttachEnergyRule to target specific attack gaps rather than just "any energy"
- Improved EvolutionRule with better board-value heuristics
- Improved RetreatRule to require meaningful position improvements
- Improved SupporterRule with keyword-based beneficial detection
- Enhanced all rule explanations with more informative trace metadata
- Fixed decision engine to properly exclude intermediate BaseRule classes from registration
- Updated test suite to validate new rule behaviors