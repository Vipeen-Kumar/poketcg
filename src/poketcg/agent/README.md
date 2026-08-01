# agent

Submission-facing orchestration and Kaggle-runtime handling.

This package owns:

- deck-selection handling,
- gameplay-observation orchestration,
- agent lifecycle branching,
- safe fallback behavior at the submission boundary,
- replay-logger wiring for whole-game traces.

This package must remain thin.

It must not own:

- raw observation parsing logic,
- card metadata loading internals,
- action classification logic,
- decision-engine rule execution logic,
- Pok\u00e9mon-specific strategy rules.
