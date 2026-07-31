# decision

Deterministic rule execution for the Pokémon TCG AI project.

This package owns:

- decision contexts and runtime configuration,
- reusable rule interfaces,
- rule registration and ordering,
- deterministic rule execution,
- serializable execution traces.

This package must remain free of:

- Monte Carlo Tree Search,
- reinforcement learning,
- neural networks,
- probabilistic evaluation,
- game-loop orchestration,
- Kaggle submission wiring.