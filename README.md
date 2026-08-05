# poketcg

Production-oriented foundation for an AI Training Agent for Kaggle's "The Pokemon Company - PTCG AI Battle Challenge Simulation".

This repository is intentionally modular. The final Kaggle submission reduces to a root-level `main.py` plus `deck.csv`, while development happens in a larger codebase that supports rule-based play, search, RL, transformer policies, self-play, and evaluation.

## Project Status

Status: Baseline agent implemented and aligned with the official Kaggle `cabt` runtime model

The repository currently includes:

- environment documentation,
- modular project architecture,
- English card database,
- observation parsing,
- typed action abstractions,
- factual game analysis,
- deterministic decision engine,
- rule library,
- replay/debug logging,
- deck validation,
- baseline agent orchestration,
- Kaggle-compatible entrypoint and submission packaging.

## Current Phase

Current completed phase: Phase 11 - Deck Validation Subsystem

This repository now has:

- a root [main.py](main.py) submission entrypoint,
- a root [deck.csv](deck.csv) submission deck file,
- an official-SDK local runner in [run_local.py](run_local.py),
- a submission packager in [build_submission.py](build_submission.py).

## Key Docs

- Environment reference: [docs/environment.md](docs/environment.md)
- Architecture reference: [docs/architecture.md](docs/architecture.md)
- Card database reference: [docs/card_database.md](docs/card_database.md)
- Parser reference: [docs/parser.md](docs/parser.md)
- Action system reference: [docs/actions.md](docs/actions.md)
- Analysis reference: [docs/analysis.md](docs/analysis.md)
- Decision engine reference: [docs/decision_engine.md](docs/decision_engine.md)
- Rules reference: [docs/rules.md](docs/rules.md)
- Debug logging reference: [docs/debug_logging.md](docs/debug_logging.md)
- Baseline agent reference: [docs/baseline_agent.md](docs/baseline_agent.md)
- Deck validation reference: [docs/deck_validation.md](docs/deck_validation.md)

# Running the Project

## Prerequisites

- Working directory: repository root  
  `C:\Users\vipee\Desktop\study\project\poketcg`
- Verified Python version: `Python 3.13`
- Core submission/runtime dependencies: Python standard library only
- Local official match dependency: `kaggle-environments>=1.14.10`

The official competition page states that submissions are executed from `/kaggle_simulations/agent/`, and the submission bundle must contain `main.py` at the root plus `deck.csv`. The current implementation also includes `src/poketcg/` and `EN_Card_Data.csv` in the submission archive so the packaged project can import its own runtime modules.

## Installation

Core repository usage:

```powershell
python --version
```

Install the official local runtime:

```powershell
pip install "kaggle-environments>=1.14.10"
```

Notes:

- The official `cabt` getting-started example uses `from kaggle_environments import make`.
- The competition description references code and configuration as of `kaggle-environments 1.14.10`.
- The local runner and submission builder both validate the baseline deck before the official SDK is invoked.

## Installing cabt Dependencies

Use the official Kaggle package install path:

```powershell
pip install "kaggle-environments>=1.14.10"
```

Based on the official sources reviewed for this audit, `cabt` is consumed through `kaggle-environments`; there is no separate documented Python package install step for our local runner.

## Running Tests

From the project root:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
python -m compileall src tests
```

## Running BaselineAgent

Smoke-test the submission entrypoint:

```powershell
python main.py
```

Expected output:

- `Baseline Kaggle entrypoint loaded successfully.`
- a reminder to use `python run_local.py` for local matches.

Programmatic smoke test:

```powershell
$env:PYTHONPATH='src'
python -c "from main import create_submission_agent; agent=create_submission_agent(); print(type(agent).__name__); print(len(agent.select_deck().card_ids))"
```

Expected output:

- `BaselineAgent`
- `60`

## Running BaselineAgent vs BaselineAgent

Official local match using `kaggle_environments.make("cabt")`:

```powershell
python run_local.py
```

More examples:

```powershell
python run_local.py --games 10
python run_local.py --games 3 --seed 42
python run_local.py --games 3 --replay
python run_local.py --games 1 --html result.html
```

If `kaggle-environments` is missing, the runner prints a helpful install message instead of raising a confusing traceback.

## Generating result.html

`run_local.py` writes an HTML replay using the official environment renderer:

```powershell
python run_local.py --html result.html
```

Single-game output:

- `result.html`

Multi-game output:

- `result_001.html`
- `result_002.html`
- and so on

## Replay Logging

Replay logs are optional and intended for local development only.

Enable them with:

```powershell
python run_local.py --replay
```

Generated files are written under:

```text
outputs/replays/
```

Expected replay artifacts:

- `outputs/replays/<game_id>.md`
- `outputs/replays/<game_id>.json`

The Kaggle submission entrypoint in [main.py](main.py) disables replay logging so the submission runtime does not depend on development logging behavior.

## Building the Kaggle Submission

Build the submission archive:

```powershell
python build_submission.py
```

Optional verification before packaging:

```powershell
python build_submission.py --run-tests
```

This creates:

```text
submission.tar.gz
```

The builder verifies:

- `main.py` exists at the repository root,
- `deck.csv` exists and contains exactly 60 integer card IDs,
- `deck.csv` passes deck legality validation,
- `deck.csv` matches the current submission agent deck,
- `EN_Card_Data.csv` exists,
- the runtime package files required by the current implementation are present,
- the output archive contains root-level `main.py` and `deck.csv`.

## Uploading to Kaggle

From the competition page:

1. Build `submission.tar.gz`.
2. Upload it under the competition's "My Submissions" tab.

The competition page states the bundle must be a `.tar.gz` archive with `main.py` at the top level and include `deck.csv`.

## Troubleshooting

### `run_local.py` says `kaggle-environments` is missing

Install it with:

```powershell
pip install "kaggle-environments>=1.14.10"
```

Then rerun:

```powershell
python run_local.py
```

### `run_local.py` fails while creating `cabt`

This usually means your installed `kaggle-environments` build does not include the `cabt` environment or has a local runtime issue. Reinstall the official package and try again.

### `build_submission.py` rejects `deck.csv`

The submission deck file must:

- exist at the repository root,
- contain exactly 60 lines with integer card IDs,
- obey the deck legality rules enforced by `src/poketcg/deck/`,
- match the current `BaselineAgent` submission deck.

If the error mentions an ACE SPEC card, the deck contains more than one copy of a card whose metadata marks it as ACE SPEC.

### `ModuleNotFoundError: No module named 'poketcg'`

For direct ad hoc module execution:

```powershell
$env:PYTHONPATH='src'
```

`main.py`, `run_local.py`, and `build_submission.py` automatically add `src/` when launched from the repository root.
