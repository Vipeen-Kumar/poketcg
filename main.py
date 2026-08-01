"""Repository-level Kaggle submission entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from poketcg.agent import BaselineAgentConfig, create_baseline_agent
from poketcg.debug.replay_logger import ReplayLoggerConfig


def create_submission_agent():
    """Create one Kaggle-compatible submission agent instance."""

    return create_baseline_agent(
        BaselineAgentConfig(
            replay=ReplayLoggerConfig(
                enabled=False,
                output_directory=Path("outputs/replays"),
                markdown=False,
                json=False,
                maximum_saved_games=0,
            )
        )
    )


_AGENT = create_submission_agent()


def agent(observation: object) -> list[int]:
    """Kaggle-facing submission function."""

    return _AGENT(observation)


def main() -> int:
    """Provide a tiny local self-check when executed directly."""

    print("Baseline Kaggle entrypoint loaded successfully.")
    print("Use `python run_local.py` to execute a local match when the official cabt SDK is installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
