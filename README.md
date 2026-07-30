# poketcg

Production-oriented foundation for an AI Training Agent for Kaggle's "The Pokemon Company - PTCG AI Battle Challenge Simulation".

This repository is intentionally modular. The final Kaggle submission will eventually reduce to `main.py` and `deck.csv`, but development happens in a scalable codebase that can support:

- rule-based agents,
- Monte Carlo Tree Search,
- reinforcement learning,
- transformer policies,
- self-play training,
- evaluation and benchmarking.

## Current Phase

This phase provides software architecture only.

Included:

- package layout,
- domain models,
- enums,
- interfaces,
- configuration,
- logging,
- exceptions,
- utility module skeletons,
- test layout.

Not included:

- gameplay logic,
- heuristics,
- policies,
- search,
- feature encoding,
- training.

## Key Docs

- Environment reference: [docs/environment.md](C:\Users\vipee\Desktop\study\project\poketcg\docs\environment.md)
- Architecture reference: [docs/architecture.md](C:\Users\vipee\Desktop\study\project\poketcg\docs\architecture.md)
