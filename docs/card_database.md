# Card Database Reference

This document describes the English card metadata database built from [EN_Card_Data.csv](C:\Users\vipee\Desktop\study\project\poketcg\EN_Card_Data.csv).

The database is the single source of truth for static card information in this project. No module outside `poketcg.cards` should read the CSV directly.

## Source Dataset

CSV columns:

1. `Card ID`
2. `Card Name`
3. `Expansion`
4. `Collection No.`
5. `Stage (Pokemon)/Type (Energy and Trainer)`
6. `Rule`
7. `Category`
8. `Previous stage`
9. `HP`
10. `Type`
11. `Weakness`
12. `Resistance (Type)`
13. `Retreat`
14. `Move Name`
15. `Cost`
16. `Damage`
17. `Effect Explanation`

Important structural observation:

- The CSV is not one row per card.
- It is one row per card text line, usually one row per attack, plus rows for passive text entries such as `[Ability] ...` and `[Tera]`.
- After normalization there are `1267` unique English cards derived from `2022` raw rows.

## Data Shapes

Detected types after normalization:

- `Card ID`: integer, contiguous range `1..1267`
- `Card Name`: non-empty string
- `Expansion`: optional string
- `Collection No.`: string
- `Stage (Pokemon)/Type (Energy and Trainer)`: categorical string
- `Rule`: optional string
- `Category`: optional string
- `Previous stage`: optional string
- `HP`: optional integer
- `Type`: optional symbol string
- `Weakness`: optional symbol string
- `Resistance (Type)`: optional symbol string
- `Retreat`: optional integer
- `Move Name`: optional string
- `Cost`: optional symbol string, including the special literal `No cost`
- `Damage`: optional string, sometimes numeric and sometimes symbolic like `30x`
- `Effect Explanation`: optional string

## Stage / Type Categories

Observed values in `Stage (Pokemon)/Type (Energy and Trainer)`:

- `Basic Pokemon`
- `Stage 1 Pokemon`
- `Stage 2 Pokemon`
- `Item`
- `Supporter`
- `Pokemon Tool`
- `Stadium`
- `Special Energy`
- `Basic Energy`

## Type Tokens

Observed type system behavior:

- Standard symbols: `{G}`, `{R}`, `{W}`, `{L}`, `{P}`, `{F}`, `{D}`, `{M}`, `{C}`
- Dragon appears as the symbol `竜` in the CSV and is normalized to `PokemonType.DRAGON`
- Rainbow-like special energy appears as `{A}` and is normalized to `PokemonType.RAINBOW`
- Team Rocket energy appears as `{Team Rocket}`
- Attack costs may also contain the colorless bullet symbol `●`
- A small number of attacks use the literal `No cost`

## Passive Text vs Attacks

The source does not provide a dedicated ability column.

The normalization rules use the source structure:

- Pokemon rows with `Move Name` and `Cost == n/a` are treated as ability-like or passive text entries
- Rows starting with `[Ability] ` become `AbilityData(kind="ability")`
- Rows equal to `[Tera]` become `AbilityData(kind="tera")`
- Rows with a real cost become `AttackData`

This keeps the source faithful without introducing gameplay logic.

## Validation Rules

The database validates:

- missing or invalid card ids
- contiguous card-id range
- empty card names
- invalid stage/type values
- malformed integer fields
- inconsistent static fields across repeated rows for the same `Card ID`
- invalid weakness, resistance, or energy token encodings

## Summary Statistics

- Total unique cards: `1267`
- Total Pokemon cards: `1056`
- Total Trainer cards: `191`
- Total Energy cards: `20`
- Cards with at least one attack: `1057`
- Cards with at least one ability-like passive text entry: `245`

### Stage Distribution

- Basic: `595`
- Stage 1: `345`
- Stage 2: `116`
- Non-Pokemon / other: `211`

### Pokemon Type Distribution

- Grass: `158`
- Psychic: `139`
- Water: `138`
- Fighting: `122`
- Darkness: `117`
- Fire: `104`
- Colorless: `104`
- Lightning: `77`
- Metal: `70`
- Dragon: `35`

### Retreat Cost

- Most common retreat cost: `1`

### HP

- Average HP across cards with numeric HP: `122.11`

### Evolution Statistics

- Cards with `Previous stage` populated: `466`

## Missing Data

Counts after normalization across unique cards:

- Missing expansion: `8`
- Missing HP: `206`
- Missing weakness: `246`
- Missing resistance: `1047`
- Missing retreat cost: `246`
- Unknown Pokemon type among Pokemon cards: `0`

## Useful Observations

1. The source is internally consistent for repeated rows of the same card. Static fields do not conflict across attack rows.
2. Card ids are contiguous from `1` to `1267`, which makes strict validation practical.
3. The CSV mixes static card metadata and text-entry rows, so normalization is required before the rest of the codebase can use it safely.
4. Exact card names are not unique. Name-based queries return multiple `CardData` records when necessary.
5. Search helpers need to be case-insensitive and work across names plus derived keyword text, not just exact names.
6. The cards layer must preserve raw source fidelity while exposing normalized enums and typed helper methods to the rest of the system.
