# PTCG AI Battle Challenge Environment Reference

This document is the project's reference for the Kaggle competition **"The Pokemon Company - PTCG AI Battle Challenge Simulation"**.

Its goal is to explain the environment contract clearly enough that a new engineer can build agents, search, RL tooling, and model policies **without needing to read the Kaggle docs first**.

This document intentionally does **not** describe heuristics or agent strategy. It only documents the environment, data structures, legal actions, and helper APIs.

## Scope

This reference is based on:

- The Kaggle competition description page for the simulation competition.
- The official `cabt` engine documentation: <https://matsuoinstitute.github.io/cabt/>
- The local card catalog file [EN_Card_Data.csv](C:\Users\vipee\Desktop\study\project\poketcg\EN_Card_Data.csv), which is useful for card IDs and metadata examples.

Important limitations:

- The workspace currently contains `EN_Card_Data.csv`, `JP_Card_Data.csv`, and two card-ID PDFs, but **not** the two sample-code PDFs mentioned in the project brief.
- Where the public docs are incomplete, this file marks items as **unclear** instead of pretending certainty.
- This document distinguishes between the **competition agent interface** and the **local SDK/helper APIs**. They are related, but not the same thing.

## Executive Summary

At a high level, the environment is a repeated cycle:

1. Kaggle creates a match.
2. Your submission provides a deck.
3. The engine runs setup.
4. Whenever a player must make a decision, the engine calls that player's `agent()`.
5. The agent receives an `Observation`.
6. The observation contains:
   - the visible game state,
   - the newly emitted logs since the previous decision,
   - the exact legal choices available right now.
7. The agent returns **indices into the legal option list**.
8. The engine applies the selected legal choices.
9. The engine either asks for another decision or ends the game.

The key design idea is:

- The environment already does **rule enforcement**.
- The agent does **choice selection**, not move construction.

That is why the normal action is just a list of option indices.

## 1. Complete Game Lifecycle

### 1.1 Competition-time lifecycle

The public competition contract is:

- Submission bundle contains `main.py` and `deck.csv`.
- Kaggle runs matches between submissions.
- During a match, the engine repeatedly calls your `agent()` with an observation.
- Your `agent()` returns either:
  - a deck selection payload at the initial deck-selection step, or
  - a list of option indices during actual gameplay decisions.

### 1.2 Lifecycle diagram

```text
Competition scheduler
        |
        v
Create match between two submissions
        |
        v
Initial call to agent()
        |
        +--> If this is the pre-battle deck-selection stage:
        |        obs.current == None
        |        obs.select  == None
        |        agent returns deck definition
        |
        v
Engine validates decks
        |
        v
Setup starts
  - shuffle
  - draw opening hands
  - check for Basic Pokemon
  - mulligan if needed
  - choose first player
  - choose Active
  - choose Bench
        |
        v
Observation arrives for a decision point
        |
        v
Agent reads obs.logs, obs.current, obs.select
        |
        v
Agent chooses indices into obs.select.option
        |
        v
Engine applies only those legal selections
        |
        +--> More sub-selections may be required
        |     (targets, cards, counts, yes/no, attack choice, etc.)
        |
        v
Turn progresses
        |
        +--> Attack resolution / KO / prize taking / special effects
        |
        v
Next decision observation
        |
        v
Repeat until terminal result
        |
        v
Game ends
  - player wins
  - player loses
  - draw
```

### 1.3 Setup and turn loop

A real game is not just `MAIN -> ATTACK -> END`. The full flow includes setup and effect sub-decisions:

```text
Deck submission
  -> setup checks
  -> mulligan loop if needed
  -> choose going first
  -> choose setup Active Pokemon
  -> choose setup Bench Pokemon
  -> turn start
  -> main-action selection
  -> zero or more effect-specific sub-selections
  -> possible attack selection
  -> attack resolution
  -> possible prize / switch / replacement / effect follow-ups
  -> turn end
  -> next player turn
  -> terminal result
```

### 1.4 What triggers another observation?

A new observation appears whenever the engine needs a player decision, for example:

- choose whether to go first,
- choose opening Active,
- choose opening Bench,
- choose a main action,
- choose a target for an attack or ability,
- choose cards to discard,
- choose a retreat destination,
- choose an attack,
- choose a number,
- answer yes/no,
- choose a special condition,
- choose prize-related or effect-related cards.

The agent is not called "once per turn". It is called **once per decision point**.

## 2. Observation Overview

The public docs define:

- `Observation.logs`
- `Observation.current`
- `Observation.select`

The docs also note:

- `current` can be `None` during the initial deck-selection phase.
- `select` can be `None` during the initial deck-selection phase.

### 2.1 Observation diagram

```text
Observation
|- logs     : what just happened since the previous decision
|- current  : visible current game state
`- select   : exact legal choices available right now
```

### 2.2 Why Observation is designed this way

The split is deliberate:

- `logs` tells you what changed.
- `current` tells you where the board stands now.
- `select` tells you what you are allowed to do next.

That lets future agent code separate:

- state tracking,
- belief/inference,
- decision logic,
- search / rollout branching.

## 3. Observation Fields in Detail

## 3.1 `Observation`

Public type: `Observation(select, logs, current, search_begin_input=None)`

### `logs`

- What it represents: events emitted since the last selection.
- Why it exists: lets an agent detect deltas without diffing the whole state manually.
- When it changes: every time something happens between decisions.
- Example values: draw, attack, HP change, switch, result.

### `current`

- What it represents: the visible current board state.
- Why it exists: main snapshot for decision making.
- When it changes: after every engine state transition.
- Example value: `State(turn=5, yourIndex=0, energyAttached=False, ...)`

### `select`

- What it represents: current selection prompt and legal options.
- Why it exists: legal-move interface between engine and agent.
- When it changes: whenever the engine asks for a new decision.
- Example value: `SelectData(type=MAIN, context=MAIN, minCount=1, maxCount=1, option=[...])`

### `search_begin_input`

- What it represents: auxiliary string input used by the search helper pathway.
- Why it exists: support for the `search_begin()` API.
- When it changes: relevant only in search-helper flows.
- Example values: undocumented in public docs.
- Status: **unclear** beyond "input to `search_begin`".

## 3.2 `State` / `Observation.current`

Public type: `State(turn, turnActionCount, yourIndex, firstPlayer, supporterPlayed, stadiumPlayed, energyAttached, retreated, result, stadium, looking, players)`

### `turn`

- What it represents: absolute turn counter.
- Why it exists: lets the agent know game progression.
- When it changes: at the start of each player's turn.
- Example values:
  - `0`: before the starting player's first turn,
  - `1`: starting player's first turn,
  - `2`: second player's first turn,
  - `3`: starting player's second turn.

### `turnActionCount`

- What it represents: number of actions already taken this turn.
- Why it exists: useful for turn-phase logic and effect sequencing.
- When it changes: after each action in the turn.
- Example values: `0`, `1`, `4`.

### `yourIndex`

- What it represents: which player this observation is for.
- Why it exists: same state schema is used for both players.
- When it changes: depends on whose decision is being requested.
- Example values: `0` or `1`.

### `firstPlayer`

- What it represents: which player was chosen to go first.
- Why it exists: some rules and planning depend on turn order.
- When it changes: set after the first-player decision; `-1` before that.
- Example values: `-1`, `0`, `1`.

### `supporterPlayed`

- What it represents: whether the once-per-turn Supporter use has already been consumed.
- Why it exists: rule enforcement and planning.
- When it changes: after playing a Supporter.
- Example values: `False`, `True`.

### `stadiumPlayed`

- What it represents: whether a Stadium has already been used this turn.
- Why it exists: rule enforcement and planning.
- When it changes: after a Stadium play.
- Example values: `False`, `True`.

### `energyAttached`

- What it represents: whether the manual once-per-turn Energy attachment has already been used.
- Why it exists: rule enforcement and planning.
- When it changes: after the manual attachment.
- Example values: `False`, `True`.

### `retreated`

- What it represents: whether the Active Pokemon has already retreated this turn.
- Why it exists: retreat is constrained.
- When it changes: after retreating.
- Example values: `False`, `True`.

### `result`

- What it represents: terminal winner index, if the battle is over.
- Why it exists: terminal-state marker.
- When it changes: only when the game ends.
- Example values:
  - `-1`: game not finished,
  - `0`: player 0 won,
  - `1`: player 1 won.

### `stadium`

- What it represents: current Stadium card in play.
- Why it exists: Stadium is part of shared global state.
- When it changes: when a Stadium enters or leaves play.
- Example values:
  - `[]`
  - `[Card(id=..., serial=..., playerIndex=...)]`

### `looking`

- What it represents: cards currently being looked at.
- Why it exists: some effects reveal or inspect cards temporarily.
- When it changes: during effects involving reveal/look/peek actions.
- Example values:
  - `None`
  - `[None, None, Card(...)]`

### `players`

- What it represents: state of both players.
- Why it exists: nearly all game reasoning is player-relative.
- When it changes: any time either side's visible board changes.
- Example value: `[PlayerState(...), PlayerState(...)]`

## 3.3 `PlayerState`

Public type: `PlayerState(active, bench, benchMax, deckCount, discard, prize, handCount, hand, poisoned, burned, asleep, paralyzed, confused)`

### `active`

- What it represents: Active Pokemon slot.
- Why it exists: battle position matters for attacks, retreat, effects.
- When it changes: switch, setup, KO replacement, card effects.
- Example values:
  - `[]`
  - `[Pokemon(...)]`
  - `[None]` for a face-down unrevealed opposing Active during setup-related hidden-information cases.

### `bench`

- What it represents: Benched Pokemon list.
- Why it exists: many effects and win conditions involve Bench.
- When it changes: setup, benching, switching, KOs, card effects.
- Example values: `[]`, `[Pokemon(...), Pokemon(...)]`

### `benchMax`

- What it represents: maximum bench size.
- Why it exists: formalizes bench-cap constraints.
- When it changes: usually stable; may only change if simulator format rules say so.
- Example value: `5`

### `deckCount`

- What it represents: number of remaining cards in deck.
- Why it exists: draw planning, milling, search constraints.
- When it changes: draws, searches, shuffles back, effects returning cards.
- Example values: `60`, `47`, `0`.

### `discard`

- What it represents: visible discard pile.
- Why it exists: discard is public information and often actionable.
- When it changes: discards, KOs, used trainers, spent effects, detached cards.
- Example values: `[]`, `[Card(id=1126,...), Card(id=1,...)]`

### `prize`

- What it represents: prize-card slots.
- Why it exists: prize count is a core win condition.
- When it changes: setup and prize collection.
- Example values:
  - `[None, None, None, None, None, None]`
  - fewer remaining prizes later in the game.

Important note:

- The docs say the **first element is the bottom prize** and the **last element is the top prize**.

### `handCount`

- What it represents: number of cards in hand.
- Why it exists: opponent hand may be hidden but count remains useful.
- When it changes: draw, play, discard, bounce, search, effect resolution.
- Example values: `7`, `3`, `12`.

### `hand`

- What it represents: actual hand cards.
- Why it exists: self hand is needed for legal play and planning.
- When it changes: same events as `handCount`.
- Example values:
  - `[Card(...), Card(...)]` for self,
  - `None` for opponent.

Important hidden-information rule:

- Your own hand is visible.
- Opponent hand contents are hidden, but `handCount` is still provided.

### `poisoned`, `burned`, `asleep`, `paralyzed`, `confused`

- What they represent: special-condition flags on the Active Pokemon.
- Why they exist: they affect legal actions, damage, and turn flow.
- When they change: attacks, abilities, recovery, switching, card effects.
- Example values: `False`, `True`.

Important note:

- These flags are on `PlayerState`, not directly on `Pokemon`, because they refer to the current Active status.

## 3.4 `Pokemon`

Public type: `Pokemon(id, serial, hp, maxHp, appearThisTurn, energies, energyCards, tools, preEvolution)`

### `id`

- What it represents: card ID.
- Why it exists: links board entity to card metadata.
- When it changes: when the Pokemon itself changes, such as evolution or devolution.
- Example values: `21`, `278`.

### `serial`

- What it represents: unique per-match identity of that physical card object.
- Why it exists: distinguishes copies of the same card ID.
- When it changes: never for that card object.
- Example values: undocumented numeric serials such as `103`, `204`.

### `hp`

- What it represents: current HP.
- Why it exists: damage state.
- When it changes: damage, healing, max-HP-related effects.
- Example values: `120`, `30`, `0`.

### `maxHp`

- What it represents: current maximum HP.
- Why it exists: evolution and effects can matter relative to max HP.
- When it changes: on card change or HP-modifying effect.
- Example values: `120`, `330`.

### `appearThisTurn`

- What it represents: whether this Pokemon entered play this turn.
- Why it exists: affects evolution and some effects.
- When it changes: when newly played or moved into a state the engine counts as appearing.
- Example values: `False`, `True`.

### `energies`

- What it represents: effective energy types currently attached.
- Why it exists: attack-cost checking and effect reasoning.
- When it changes: attachments, detachments, movement, special-energy effects.
- Example values:
  - `[]`
  - `[FIGHTING, COLORLESS]`
  - `[PSYCHIC, DARKNESS]`

### `energyCards`

- What it represents: attached energy-card objects.
- Why it exists: some effects care about physical attached cards, not just energy types.
- When it changes: same times as `energies`.
- Example values: `[Card(id=1,...)]`

### `tools`

- What it represents: attached Pokemon Tool cards.
- Why it exists: tools are visible and affect legal actions.
- When it changes: tool attach/remove/discard/move effects.
- Example values: `[]`, `[Card(id=..., serial=..., playerIndex=...)]`

### `preEvolution`

- What it represents: stack of earlier evolution cards under the current Pokemon.
- Why it exists: devolution and history-dependent effects.
- When it changes: evolution, devolution.
- Example values: `[]`, `[Card(id=..., ...)]`

## 3.5 `Card`

Public type: `Card(id, serial, playerIndex)`

### `id`

- What it represents: card ID from the card catalog.
- Why it exists: stable link to metadata.
- When it changes: never for that card.
- Example values: `1`, `21`, `1126`.

### `serial`

- What it represents: unique per-match card instance ID.
- Why it exists: differentiates duplicate card IDs.
- When it changes: never for that card object.
- Example values: `17`, `91`, `244`.

### `playerIndex`

- What it represents: owner of that card object.
- Why it exists: ownership matters for legal targeting and logging.
- When it changes: usually stable; ownership transfer rules are not documented in the public reference.
- Example values: `0`, `1`.

## 3.6 `SelectData`

Public type: `SelectData(type, context, minCount, maxCount, remainDamageCounter, remainEnergyCost, option, deck, contextCard, effect)`

This is the heart of the action interface.

### `type`

- What it represents: general shape of the current selection.
- Why it exists: tells the agent how to interpret `option`.
- When it changes: every new selection prompt.
- Example values: `MAIN`, `CARD`, `ATTACK`, `YES_NO`.

### `context`

- What it represents: specific purpose of the selection.
- Why it exists: tells the agent what decision scenario it is in.
- When it changes: every new selection prompt.
- Example values: `MAIN`, `SETUP_ACTIVE_POKEMON`, `DISCARD`, `ATTACK`.

### `minCount`, `maxCount`

- What they represent: lower and upper bounds on how many option indices must be returned.
- Why they exist: some prompts are single-select, some are multi-select, some are optional.
- When they change: per selection prompt.
- Example values:
  - `1/1` for exactly one choice,
  - `0/1` for optional single choice,
  - `1/3` for choose up to three but at least one.

Important note:

- The agent returns a **list of option indices**, and its length must satisfy these bounds.

### `remainDamageCounter`

- What it represents: remaining number of damage counters that may still be placed.
- Why it exists: effect-resolution helper.
- When it changes: during damage-counter placement sub-selections.
- Example values: `0`, `1`, `3`.

### `remainEnergyCost`

- What it represents: remaining energy requirement for energy-selection prompts.
- Why it exists: effect-resolution helper for energy-related choices.
- When it changes: during energy-payment or energy-selection subflows.
- Example values: `0`, `1`, `2`.

### `option`

- What it represents: exact legal options for the current decision.
- Why it exists: this is the legal action set.
- When it changes: every decision point.
- Example values: `[Option(type=PLAY,...), Option(type=ATTACK,...), Option(type=END)]`

### `deck`

- What it represents: deck cards exposed for a selection.
- Why it exists: some effects let the player choose from deck contents.
- When it changes: only during deck-inspection/search-style prompts.
- Example values:
  - `None`
  - `[Card(...), Card(...)]`

### `contextCard`

- What it represents: the card specifically associated with the current context.
- Why it exists: useful when a yes/no activation prompt refers to a specific card.
- When it changes: populated especially for activation-type contexts.
- Example values: `None`, `Card(id=1126, ...)`

### `effect`

- What it represents: the card whose effect is currently being resolved.
- Why it exists: effect sub-decisions often need to know their source.
- When it changes: during effect resolution.
- Example values: `None`, `Card(id=1126, ...)`

## 3.7 `Option`

Public type: `Option(type, number=None, area=None, index=None, playerIndex=None, toolIndex=None, energyIndex=None, count=None, inPlayArea=None, inPlayIndex=None, attackId=None, cardId=None, serial=None, specialConditionType=None)`

An `Option` is not the action itself. It is a legal candidate in the current option list. The action you return is the **index** of that option.

### Core locator fields

### `type`

- What it represents: which kind of selectable thing this option refers to.
- Why it exists: main discriminator.
- Example values: `PLAY`, `CARD`, `ATTACK`, `YES`, `ENERGY`.

### `area`

- What it represents: where the relevant card currently is.
- Why it exists: needed for card-targeting semantics.
- Example values: `HAND`, `ACTIVE`, `BENCH`, `DISCARD`, `PRIZE`.

### `index`

- What it represents: index inside the specified area.
- Why it exists: identifies the target within that area.
- Example values: `0`, `2`, `5`.

### `playerIndex`

- What it represents: owner of the referenced card or Pokemon.
- Why it exists: target ownership matters.
- Example values: `0`, `1`.

### `serial`

- What it represents: exact physical card instance.
- Why it exists: duplicates need disambiguation.
- Example values: numeric per-match IDs.

### Attached-card fields

### `toolIndex`

- What it represents: position of a Tool among attached tools.
- Why it exists: tool-selection prompts.

### `energyIndex`

- What it represents: position of an Energy among attached energies.
- Why it exists: energy-selection prompts.

### `count`

- What it represents: how many energy units the option corresponds to.
- Why it exists: some energy cards provide multiple units or special mappings.

### In-play target fields

### `inPlayArea`

- What it represents: area of the in-play Pokemon being referred to.
- Why it exists: attach/evolve options refer both to a card and to a board target.

### `inPlayIndex`

- What it represents: index of the in-play Pokemon target.
- Why it exists: same reason as `inPlayArea`.

### Other semantic fields

### `number`

- What it represents: numeric choice for `NUMBER` options.
- Why it exists: count-selection prompts.
- Example values: `1`, `2`, `3`.

### `attackId`

- What it represents: ID of the attack being selected.
- Why it exists: attack-choice prompts.

### `cardId`

- What it represents: card ID associated with the option.
- Why it exists: skill and card-specific prompts.

### `specialConditionType`

- What it represents: special condition named by the option.
- Why it exists: condition-selection prompts.
- Example values: `POISON`, `SLEEP`.

## 3.8 `Log`

Public type: `Log(type, ...)`

Logs are event records, not state snapshots. They explain what happened since the previous decision.

### Why logs matter

They are useful for:

- state-delta tracking,
- debugging,
- replay parsing,
- training data extraction,
- search tree explanation,
- reward shaping later.

### Log types documented publicly

- `SHUFFLE`
- `HAS_BASIC_POKEMON`
- `TURN_START`
- `TURN_END`
- `DRAW`
- `DRAW_REVERSE`
- `MOVE_CARD`
- `MOVE_CARD_REVERSE`
- `SWITCH`
- `CHANGE`
- `PLAY`
- `ATTACH`
- `EVOLVE`
- `DEVOLVE`
- `MOVE_ATTACHED`
- `ATTACK`
- `HP_CHANGE`
- `POISONED`
- `BURNED`
- `ASLEEP`
- `PARALYZED`
- `CONFUSED`
- `COIN`
- `RESULT`

### Key result semantics

For `RESULT`, the docs state:

- `result`: `0 = player 0 win`, `1 = player 1 win`, `2 = draw`
- `reason`:
  - `1 = 0 prize cards`
  - `2 = no deck`
  - `3 = no Active Pokemon`
  - `4 = card effect`

## 4. SelectType vs SelectContext

These are related but different.

### `SelectType`

This tells you the **shape** of the choice.

Examples:

- `MAIN`
- `CARD`
- `ATTACHED_CARD`
- `ENERGY`
- `ATTACK`
- `EVOLVE`
- `COUNT`
- `YES_NO`
- `SPECIAL_CONDITION`

### `SelectContext`

This tells you the **meaning** of the choice in the current situation.

Examples:

- `MAIN`
- `SETUP_ACTIVE_POKEMON`
- `DISCARD`
- `ATTACK`
- `DRAW_COUNT`
- `MULLIGAN`

Rule of thumb:

- `type` answers: "What kind of thing am I selecting?"
- `context` answers: "Why am I selecting it right now?"

## 5. Every SelectContext

The public docs define 49 `SelectContext` values. The table below explains what decision happens in each one.

### 5.1 Main and setup contexts

| Context | Meaning | Typical decision |
|---|---|---|
| `MAIN` | Main action menu | Choose play, attach, evolve, ability, retreat, attack, or end turn |
| `SETUP_ACTIVE_POKEMON` | Opening setup Active choice | Choose which Basic Pokemon starts Active |
| `SETUP_BENCH_POKEMON` | Opening setup Bench choice | Choose which Basics to bench during setup |
| `IS_FIRST` | Decide who goes first | Choose yes/no for first-player selection |
| `MULLIGAN` | Decide whether to redraw opening hand | Handle mulligan flow |

### 5.2 Movement and positioning contexts

| Context | Meaning | Typical decision |
|---|---|---|
| `SWITCH` | Switch with Active | Choose Bench Pokemon to become Active |
| `TO_ACTIVE` | Move something to Active | Choose replacement or moved Pokemon |
| `TO_BENCH` | Move something to Bench | Choose destination-to-bench card |
| `TO_FIELD` | Put into play | Choose a card to place onto the field |
| `NOT_MOVE` | Leave in place | Choose a card that should not move |

### 5.3 Card relocation contexts

| Context | Meaning | Typical decision |
|---|---|---|
| `TO_HAND` | Return card to hand | Choose which card gets bounced |
| `DISCARD` | Discard card | Choose a card to discard |
| `TO_DECK` | Return card to deck | Choose which card goes back into deck |
| `TO_DECK_BOTTOM` | Return card to bottom of deck | Choose which card goes to bottom |
| `TO_PRIZE` | Add card to prizes | Choose card to become prize |
| `LOOK` | Look at card | Choose card to reveal/inspect |

### 5.4 Damage and healing contexts

| Context | Meaning | Typical decision |
|---|---|---|
| `DAMAGE_COUNTER` | Place damage counters under constrained rules | Choose target Pokemon for counter placement |
| `DAMAGE_COUNTER_ANY` | Freely place damage counters | Choose target under broader effect rules |
| `DAMAGE` | Deal damage | Choose damage target |
| `REMOVE_DAMAGE_COUNTER` | Remove damage counters | Choose healing/removal target |
| `HEAL` | Heal | Choose Pokemon to heal |
| `DAMAGE_COUNTER_COUNT` | Choose how many counters to place | Numeric count selection |
| `REMOVE_DAMAGE_COUNTER_COUNT` | Choose how many counters to remove | Numeric count selection |

### 5.5 Evolution contexts

| Context | Meaning | Typical decision |
|---|---|---|
| `EVOLVES_FROM` | Choose base Pokemon | Select which Pokemon evolves |
| `EVOLVES_TO` | Choose evolution card | Select which evolution is applied |
| `EVOLVE` | Combined evolve selection | Select evolution option pairing source and target |
| `DEVOLVE` | Choose Pokemon to devolve | Select target for devolution |
| `MORE_DEVOLVE` | Decide whether to continue devolving | Yes/no |

### 5.6 Attachment and detachment contexts

| Context | Meaning | Typical decision |
|---|---|---|
| `ATTACH_FROM` | Choose Pokemon to attach to | Select in-play recipient |
| `ATTACH_TO` | Choose card to attach | Select attachment card |
| `DETACH_FROM` | Choose Pokemon to remove from | Select source of detachment |
| `DISCARD_ENERGY_CARD` | Discard attached energy card | Choose specific attached energy card |
| `DISCARD_TOOL_CARD` | Discard attached tool card | Choose specific attached tool card |
| `SWITCH_ENERGY_CARD` | Switch attached energy card | Choose specific attached energy card |
| `DISCARD_CARD_OR_ATTACHED_CARD` | Discard either a card or attached card | Choose from both kinds of targets |
| `DISCARD_ENERGY` | Discard energy unit | Choose energy contribution to discard |
| `TO_HAND_ENERGY` | Return energy to hand | Choose energy to bounce |
| `TO_DECK_ENERGY` | Return energy to deck | Choose energy to shuffle back |
| `SWITCH_ENERGY` | Switch energy allocation | Choose energy to move/swap |

### 5.7 Attack, skill, and target contexts

| Context | Meaning | Typical decision |
|---|---|---|
| `SKILL_ORDER` | Order skill activations | Choose ability ordering |
| `ATTACK` | Choose attack to use | Pick one attack from the attack menu |
| `DISABLE_ATTACK` | Choose attack to disable | Select which attack becomes unusable |
| `EFFECT_TARGET` | Choose effect target | Select card/Pokemon affected by an effect |
| `ACTIVATE` | Decide whether to activate an effect | Yes/no |
| `FIRST_EFFECT` | Decide whether to use first effect | Yes/no |

### 5.8 Count, coin, and condition contexts

| Context | Meaning | Typical decision |
|---|---|---|
| `DRAW_COUNT` | Choose number of cards to draw | Numeric count |
| `COIN_HEAD` | Choose heads or tails | Yes/no-shaped coin choice when manual coin is enabled |
| `AFFECT_SPECIAL_CONDITION` | Choose condition to apply or affect | Select special condition |
| `RECOVER_SPECIAL_CONDITION` | Choose condition to recover | Select special condition |

### 5.9 Contexts that are easy to confuse

### `SWITCH` vs `TO_ACTIVE`

- `SWITCH` usually means selecting a Bench Pokemon to replace the current Active.
- `TO_ACTIVE` is broader language: move/select something into the Active Spot.
- In practice, both are "choose the new Active" style contexts, but the engine distinguishes the scenario.

### `DAMAGE_COUNTER` vs `DAMAGE`

- `DAMAGE_COUNTER` means direct damage-counter placement.
- `DAMAGE` means damage dealing more generally.
- This matters because some effects care whether damage was placed as counters versus dealt as attack damage.

### `ATTACH_FROM` vs `ATTACH_TO`

The public short descriptions are slightly awkward:

- `ATTACH_FROM`: docs say "Select Pokemon to attach the card to"
- `ATTACH_TO`: docs say "Select card to attach to the Pokemon"

So the pairing is effectively:

- one side identifies the recipient Pokemon,
- the other side identifies the card being attached.

## 6. Every OptionType

The public docs define these `OptionType` values.

### `NUMBER`

- Meaning: choose a number.
- Appears when: count-selection prompts such as draw count or damage-counter count.
- Example usage: choose `2` from options `[1, 2, 3]`.

### `YES`

- Meaning: affirmative answer.
- Appears when: `YES_NO` selections such as activation, first-player choice, mulligan.
- Example usage: choose to activate an ability.

### `NO`

- Meaning: negative answer.
- Appears when: `YES_NO` prompts.
- Example usage: decline an optional effect.

### `CARD`

- Meaning: select a card from a zone.
- Appears when: setup, discard, targeting, return-to-hand, move-to-deck, switch-like contexts.
- Example usage: choose hand index `3` to play/discard, or choose bench index `1` as a target.

### `TOOL_CARD`

- Meaning: select a Tool attached to a Pokemon.
- Appears when: tool-discard or tool-targeting effects.
- Example usage: remove a specific attached tool from a Pokemon.

### `ENERGY_CARD`

- Meaning: select an attached Energy card object.
- Appears when: attached-energy discard or movement.
- Example usage: choose the second attached energy on the Active Pokemon.

### `ENERGY`

- Meaning: select an energy unit / energy contribution.
- Appears when: energy-cost-related sub-selections.
- Example usage: choose which attached energy counts toward a discard or switch effect.

### `PLAY`

- Meaning: play a card from hand.
- Appears when: main-action menu.
- Example usage: choose a Supporter, Item, Basic Pokemon, Tool, or Stadium from hand if legal.

### `ATTACH`

- Meaning: attach a card to an in-play Pokemon.
- Appears when: main-action attach menu or effect-based attach prompts.
- Example usage: attach a Basic Energy from hand to your Active or Bench.

### `EVOLVE`

- Meaning: evolve a Pokemon using a specific evolution card and target.
- Appears when: evolution decisions.
- Example usage: choose the pairing "this hand card evolves that Benched Pokemon".

### `ABILITY`

- Meaning: use a card's Ability.
- Appears when: main-action menu or ability-related prompts.
- Example usage: activate a Pokemon Ability from Active or Bench.

### `DISCARD`

- Meaning: discard a card currently in play.
- Appears when: costs or effects require discarding an in-play card.
- Example usage: discard a Stadium or attached object if legal.

### `RETREAT`

- Meaning: retreat the Active Pokemon.
- Appears when: retreat is legal in the main menu.
- Example usage: pay retreat and move a Bench Pokemon active through follow-up selections.

### `ATTACK`

- Meaning: use one specific attack.
- Appears when: attack-selection context.
- Example usage: choose one of the Active Pokemon's attacks by `attackId`.

### `END`

- Meaning: end the turn.
- Appears when: main-action menu.
- Example usage: do nothing else and pass.

### `SKILL`

- Meaning: choose a skill to activate.
- Appears when: skill-order or skill-selection prompts.
- Example usage: resolve triggered abilities in a chosen order.

### `SPECIAL_CONDITION`

- Meaning: choose a special condition.
- Appears when: apply/recover special-condition prompts.
- Example usage: select `POISON` or `SLEEP`.

## 7. Legal Actions and Why the Agent Returns Indices

The environment is designed so that the engine only presents legal choices.

The Kaggle competition page says:

- each turn your agent receives an observation,
- the observation includes a list of legal options,
- your agent returns the indices of the options it selects,
- the engine only ever presents legal moves.

### 7.1 Why this matters

This means the agent does not need to:

- check whether a card is playable under game rules,
- reconstruct attack-cost legality from scratch,
- verify whether retreat is currently legal,
- determine whether a target is valid under the exact effect wording.

The engine already did that.

### 7.2 Action format

Conceptually:

```text
obs.select.option = [option0, option1, option2, ...]
agent returns [chosen_index0, chosen_index1, ...]
```

If the legal options are:

```text
0 -> PLAY card at hand index 1
1 -> ATTACH energy from hand to bench index 0
2 -> ATTACK attackId 17
3 -> END turn
```

then returning `[2]` means:

- "choose the third legal option, which is the attack option."

### 7.3 Why invalid game-rule moves normally do not happen

Because:

- legal filtering happens before the observation reaches the agent,
- the agent chooses only among already-approved options.

### 7.4 Important nuance

The phrase "invalid moves never happen" is true only in the **game-rule** sense.

You can still cause an invalid action error if your agent:

- returns an out-of-range index,
- returns the wrong number of indices,
- returns the wrong type,
- violates the action schema itself.

So the real guarantee is:

- the option list contains only legal game moves,
- but the agent must still return a syntactically valid selection list.

## 8. Deck Selection

## 8.1 Why the first call has `obs.select == None`

The public docs explicitly state:

- `Observation.current` is `None` during the initial deck-selection phase.
- `Observation.select` is `None` during the initial deck-selection phase.

This means the very first call is **not a normal in-battle decision prompt**.

It is a pre-battle handshake phase.

### 8.2 Why the agent returns a deck list there

Reasoning:

- Before the engine can build a real board state, it must know which deck the player is using.
- Until the deck is fixed, there is no normal board state and no normal legal move list.
- Therefore `current` and `select` are absent.

Your project brief also states that on this first call the agent returns the deck list. That fits the documented "deck-selection phase" semantics.

Status:

- `obs.current is None` and `obs.select is None`: **confirmed by public docs**.
- "the first call returns the deck list": **consistent with competition behavior and your brief, but not spelled out in the public `cabt` API page we found**.

### 8.3 Relationship to `deck.csv`

The Kaggle competition page requires submissions to include `deck.csv`.

During development, you may also have an agent-side deck-return path in local tooling. Treat these as related but slightly different layers:

- competition packaging requirement: `deck.csv` must exist in the submission bundle,
- agent/development interface: initial deck-selection phase may ask for the deck payload.

For this project, we should design deck handling so both are supported cleanly.

## 9. Battle Flow

## 9.1 Pre-game and setup

Before the first normal turn:

1. Decks are chosen and validated.
2. Decks are shuffled.
3. Opening hands are drawn.
4. Basic-Pokemon availability is checked.
5. Mulligans happen if needed.
6. First player is determined.
7. Active Pokemon is selected.
8. Benched Pokemon are selected.

Relevant logs and contexts:

- `SHUFFLE`
- `HAS_BASIC_POKEMON`
- `MULLIGAN`
- `IS_FIRST`
- `SETUP_ACTIVE_POKEMON`
- `SETUP_BENCH_POKEMON`

## 9.2 Beginning of turn

At turn start:

- `TURN_START` is logged.
- `turn` increments.
- the acting player receives observations for any needed decisions.

The docs do not provide a separate formal "beginning phase" object. Instead, turn state is represented through:

- `turn`,
- `turnActionCount`,
- current status flags,
- follow-up selections and logs.

## 9.3 Main phase

The main decision menu is `SelectContext.MAIN` with `SelectType.MAIN`.

The docs say this menu can include these option types:

- `PLAY`
- `ATTACH`
- `EVOLVE`
- `ABILITY`
- `DISCARD`
- `RETREAT`
- `ATTACK`
- `END`

This is where most agent policy work will eventually focus.

## 9.4 Attack phase

Attacking is not a separate outer API shape. It is reached through legal options.

Typical flow:

1. main menu includes an `ATTACK`-type option or attack pathway,
2. attack choice may enter `SelectContext.ATTACK`,
3. agent selects one attack,
4. effect sub-selections may follow,
5. engine resolves damage, status, switches, KOs, etc.

Relevant logs:

- `ATTACK`
- `HP_CHANGE`
- special condition logs
- `SWITCH`
- `CHANGE`
- `RESULT`

## 9.5 End turn

The turn can end either:

- explicitly via an `END` option, or
- implicitly after attack resolution if the rules/effect sequence dictates that the turn is over.

Relevant log:

- `TURN_END`

## 9.6 Prize collection

Prize state is represented in `PlayerState.prize`.

The public docs define the structure of the prize list, but they do **not** fully describe a separate prize-selection API in the snippets we found.

What is confirmed:

- prize cards exist as a visible slot list with hidden entries represented by `None`,
- the result reason `1` means a player reached `0 prize cards`.

What is still unclear from public docs:

- whether all prize-taking is automatic in every case,
- whether there are effect-driven contexts that interact with prize choice beyond the documented `TO_PRIZE`.

## 9.7 Win / loss / draw

A battle is terminal when `State.result != -1` or a `RESULT` log appears.

Documented result reasons:

- `1`: player reached `0 prize cards`
- `2`: no deck
- `3`: no Active Pokemon
- `4`: card effect

Draw is represented in logs as `result = 2`.

## 10. Helper APIs

These APIs are part of the `cabt` SDK and are most useful for local development, testing, search, debugging, and training pipelines.

They are not the same thing as the minimal competition-time `agent(obs)` contract.

## 10.1 `all_card_data()`

- Purpose: returns metadata for all available cards.
- Input: none.
- Output: `list[CardData]`.
- When we will use it later:
  - build the card database,
  - map card IDs to names/types/stats,
  - validate deck files,
  - enrich observations with static metadata,
  - build feature encoders.

Important static fields in `CardData`:

- `cardId`
- `name`
- `cardType`
- `retreatCost`
- `hp`
- `weakness`
- `resistance`
- `energyType`
- `basic`
- `stage1`
- `stage2`
- `ex`
- `megaEx`
- `tera`
- `aceSpec`
- `evolvesFrom`
- `skills`
- `attacks`

Example local card-catalog facts from [EN_Card_Data.csv](C:\Users\vipee\Desktop\study\project\poketcg\EN_Card_Data.csv):

- Card ID `1`: `Basic {G} Energy`
- Card ID `21`: `Scrafty`
- Card ID `278`: `Lillie's Cutiefly`
- Card ID `1126`: `Precious Trolley` with rule `ACE SPEC`

## 10.2 `all_attack()`

- Purpose: returns attack metadata.
- Input: none.
- Output: `list[Attack]`.
- When we will use it later:
  - map `attackId` to name/text/damage/cost,
  - build attack embeddings/features,
  - explain action choices,
  - support search and rollout policies.

Important fields:

- `attackId`
- `name`
- `text`
- `damage`
- `energies`

## 10.3 `to_observation_class(obs)`

- Purpose: convert raw dict observation to dataclass form.
- Input: raw observation dictionary.
- Output: `Observation`.
- When we will use it later:
  - typed parsing,
  - cleaner policy/search code,
  - safer internal adapters and unit tests.

This is especially useful because competition observations may enter the agent as plain dictionaries.

## 10.4 `search_begin(...)`

- Purpose: initialize a search state from the current observation plus hidden-information guesses.
- Inputs:
  - `agent_observation`
  - `your_deck`
  - `your_prize`
  - `opponent_deck`
  - `opponent_prize`
  - `opponent_hand`
  - `opponent_active`
  - `manual_coin=False`
- Output: `SearchState`
- When we will use it later:
  - MCTS or tree search,
  - hidden-information hypothesis branching,
  - local rollout generation,
  - evaluation tooling.

Important design implication:

- Search is not purely from public state.
- It requires guesses for hidden zones such as opponent deck, prize, and hand.

That is a major clue about how future search and RL state estimation should be architected.

## 10.5 `search_step(search_id, select)`

- Purpose: advance a search branch by applying a selected option list.
- Input:
  - `search_id`
  - `select` as chosen option indices
- Output: next `SearchState`
- When we will use it later:
  - simulate action branches,
  - build lookahead trees,
  - value backup and rollout tooling.

## 10.6 `search_end()`

- Purpose: end the current search and reuse memory.
- Input: none.
- Output: `None`
- When we will use it later:
  - clean search sessions between planning calls,
  - avoid leaking native memory/resources.

## 10.7 `search_release(search_id)`

- Purpose: explicitly delete one search state.
- Input: `search_id`
- Output: `None`
- When we will use it later:
  - prune branches,
  - release branch states early in tree search.

## 10.8 `battle_start(deck0, deck1)`

- Purpose: start a local battle between two decks.
- Input:
  - `deck0`: 60 card IDs
  - `deck1`: 60 card IDs
- Output: `(Observation | None, StartData)` according to the overview docs, and `tuple[dict | None, StartData]` on the game API page.
- When we will use it later:
  - local battle harness,
  - deterministic tests,
  - self-play scaffolding,
  - replay/debug runs.

Important note:

- The docs say it raises `ValueError` if either deck does not contain exactly 60 cards.

## 10.9 `battle_select(select_list)`

- Purpose: apply one local selection step and get the next observation.
- Input: list of option indices.
- Output: updated observation dict.
- When we will use it later:
  - local simulation loops,
  - testing legal-action handlers,
  - offline data generation.

Important note:

- The docs say it can raise `IndexError` if the selection index is invalid.

## 10.10 `battle_finish()`

- Purpose: clean up current local battle resources.
- Input: none.
- Output: none.
- When we will use it later:
  - battle harness cleanup,
  - integration testing,
  - bulk self-play jobs.

## 10.11 `visualize_data()`

- Purpose: retrieve a human-readable/debuggable representation of current board state.
- Input: none.
- Output: `str`
- When we will use it later:
  - debugging,
  - replay inspection,
  - sanity-checking local environment wrappers.

## 11. Local SDK vs Competition Agent Contract

It is important not to mix these layers.

### Competition-time agent contract

Your submission's real runtime responsibility is small:

```text
agent(observation) -> deck payload or list[int]
```

### Local SDK contract

For development, the SDK exposes many more tools:

- `battle_start`
- `battle_select`
- `battle_finish`
- `all_card_data`
- `all_attack`
- `search_begin`
- `search_step`
- `search_end`
- `search_release`
- `to_observation_class`

Practical conclusion:

- Keep the production `agent()` thin.
- Put richer simulation/search/state code in internal modules.

That matches this project's planned modular architecture well.

## 12. Recommended Internal Architecture Boundary

Even though this document does not implement code, the environment strongly suggests the following separation:

```text
Raw Observation Dict
        |
        v
Observation Parser / Adapter
        |
        v
Typed State + Legal Option View
        |
        +--> State Tracker
        +--> Belief / Hidden-Info Tracker
        +--> Feature Encoder
        +--> Replay / Log Analyzer
        |
        v
Decision Engine
        |
        +--> Rule-based policy later
        +--> MCTS later
        +--> RL policy later
        +--> Transformer policy later
        |
        v
Selected Option Indices
        |
        v
Environment
```

For search specifically:

```text
Observation
   + guessed hidden cards
        |
        v
search_begin()
        |
        v
SearchState
        |
        v
search_step() repeatedly
        |
        v
Tree expansion / rollout / evaluation
        |
        v
choose root action index
```

## 13. Known Hidden-Information Boundaries

The environment is not full-information.

Confirmed from docs:

- opponent hand contents are hidden: `hand=None`, `handCount` visible,
- prize cards may be face-down: `None`,
- opponent Active may sometimes be face-down in setup-related states,
- search helpers require guessed hidden-zone card IDs.

This means future AI components will likely need:

- public-state features,
- hidden-state beliefs,
- rollout assumptions,
- sampled determinizations for search.

## 14. Important Practical Rules for Future Engineers

### Rule 1

Do not infer legality yourself if `obs.select.option` already tells you the legal choices.

### Rule 2

Always route decision logic by both:

- `obs.select.type`
- `obs.select.context`

Using only one is not enough.

### Rule 3

Treat `Option.serial` and `Card.serial` as instance identity, not deck identity.

### Rule 4

Do not assume the agent is called once per turn. It is called once per decision point.

### Rule 5

Do not assume all choices are single-select. Respect:

- `minCount`
- `maxCount`

### Rule 6

Do not confuse:

- static card metadata (`all_card_data`, CSV catalog)
- dynamic battle state (`Observation.current`)
- legal action set (`Observation.select`)

### Rule 7

For debugging and training data, logs are first-class information, not optional extras.

## 15. Unclear or Incompletely Documented Areas

These should be treated as open questions until we inspect the missing sample PDFs or run local SDK experiments.

### Unclear area 1: exact competition-time deck-return payload

We know:

- the initial phase has `current=None` and `select=None`,
- the project brief says the agent returns the deck list.

But the exact wire shape is not documented in the public `cabt` API pages we found.

### Unclear area 2: prize-taking interaction details

The public docs define prize storage and terminal result reasons, but they do not fully spell out whether every prize-taking situation is automatic or whether some effects produce separate player choices.

### Unclear area 3: `search_begin_input`

The docs only say it is "input to the search_begin function." Public detail is limited.

### Unclear area 4: full simulator-rule differences from official tabletop rules

The competition page says there are some differences between official Pokemon TCG rules and simulator behavior, but those differences were not included in the public snippets gathered here.

### Unclear area 5: exact semantics of some similarly named movement contexts

Examples:

- `SWITCH`
- `TO_ACTIVE`
- `TO_FIELD`
- `CHANGE`

The docs provide short descriptions, but edge-case differences are best verified by local experiments later.

## 16. Source Notes

Primary source links used for this document:

- Kaggle competition description: <https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/overview/description>
- `cabt` documentation home: <https://matsuoinstitute.github.io/cabt/>
- `cabt` API reference: <https://matsuoinstitute.github.io/cabt/api.html>
- `cabt` game API: <https://matsuoinstitute.github.io/cabt/game.html>
- `cabt` sim module: <https://matsuoinstitute.github.io/cabt/sim.html>

Local supporting artifact:

- [EN_Card_Data.csv](C:\Users\vipee\Desktop\study\project\poketcg\EN_Card_Data.csv)

## 17. Bottom Line

The environment is fundamentally:

- a **partially observable**, **legal-action-filtered**, **decision-point-driven** battle simulator.

Your future AI stack should therefore be built around:

- typed observation parsing,
- option-index action selection,
- context-aware decision routing,
- hidden-information handling,
- local simulation/search helpers,
- clean separation between competition agent I/O and internal AI modules.

That is the correct foundation for later adding:

- rule-based policies,
- MCTS,
- RL,
- transformer policies.
