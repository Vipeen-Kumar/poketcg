"""Official kaggle-environments local runner for the baseline submission agent."""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from main import create_submission_agent
from poketcg.agent import BaselineAgentConfig, create_baseline_agent
from poketcg.debug.replay_logger import ReplayLoggerConfig


class LocalRunnerError(RuntimeError):
    """Raised when the local Kaggle runner cannot be started."""


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the local-runner CLI."""

    parser = argparse.ArgumentParser(description="Run BaselineAgent vs BaselineAgent with kaggle-environments.")
    parser.add_argument("--games", type=int, default=1, help="Number of local matches to run.")
    parser.add_argument("--seed", type=int, default=None, help="Optional environment seed.")
    parser.add_argument(
        "--replay",
        action="store_true",
        help="Enable replay logging under outputs/replays/ during local matches.",
    )
    parser.add_argument(
        "--html",
        default="result.html",
        help="HTML replay output path for a single game, or filename prefix for multiple games.",
    )
    return parser


def load_kaggle_make():
    """Load the official kaggle-environments make() entrypoint."""

    try:
        module = importlib.import_module("kaggle_environments")
    except ModuleNotFoundError as error:
        raise LocalRunnerError(
            "The local runner requires the official `kaggle-environments` package.\n"
            "Install it with:\n"
            "  pip install \"kaggle-environments>=1.14.10\"\n"
            "Then rerun:\n"
            "  python run_local.py"
        ) from error

    make = getattr(module, "make", None)
    if not callable(make):
        raise LocalRunnerError(
            "The installed `kaggle-environments` package does not expose a callable `make` function."
        )
    return make


def build_local_agent(*, replay_enabled: bool, game_id_prefix: str):
    """Create one local baseline agent with optional replay logging enabled."""

    if not replay_enabled:
        return create_submission_agent()

    return create_baseline_agent(
        BaselineAgentConfig(
            game_id_prefix=game_id_prefix,
            replay=ReplayLoggerConfig(
                enabled=True,
                output_directory=Path("outputs/replays"),
                markdown=True,
                json=True,
                maximum_saved_games=100,
            ),
        )
    )


def load_deck_csv(path: Path | None = None) -> list[int]:
    """Load the submission deck from deck.csv."""

    deck_path = path or (PROJECT_ROOT / "deck.csv")
    if not deck_path.exists():
        raise LocalRunnerError(f"Required deck file not found: {deck_path}")

    deck: list[int] = []
    for line_number, raw_line in enumerate(deck_path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        try:
            deck.append(int(stripped))
        except ValueError as error:
            raise LocalRunnerError(f"Invalid card id in {deck_path} on line {line_number}: {stripped!r}") from error

    if len(deck) != 60:
        raise LocalRunnerError(f"{deck_path} must contain exactly 60 card ids; found {len(deck)}.")
    return deck


def save_result_html(env, output_path: Path) -> None:
    """Render one HTML replay file from the official environment."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    html = env.render(mode="html")
    if not isinstance(html, str):
        raise LocalRunnerError("kaggle-environments did not return HTML replay output.")
    output_path.write_text(html, encoding="utf-8")


def _html_output_path(base_path: Path, game_number: int, total_games: int) -> Path:
    if total_games == 1:
        return base_path
    stem = base_path.stem or "result"
    suffix = base_path.suffix or ".html"
    return base_path.with_name(f"{stem}_{game_number:03d}{suffix}")


def run_local_games(*, games: int, replay: bool, seed: int | None, html_path: str) -> int:
    """Run one or more local official cabt matches."""

    if games < 1:
        raise LocalRunnerError("`--games` must be at least 1.")

    make = load_kaggle_make()
    submission_deck = load_deck_csv()
    base_html_path = Path(html_path)

    for game_number in range(1, games + 1):
        game_seed = None if seed is None else seed + (game_number - 1)
        print(f"[Game {game_number}/{games}] Creating official cabt environment.")
        try:
            env = make(
                "cabt",
                configuration={
                    "decks": [submission_deck, submission_deck],
                    **({ "seed": game_seed } if game_seed is not None else {}),
                },
                debug=True,
            )
        except Exception as error:
            raise LocalRunnerError(
                "Failed to create the official `cabt` environment through `kaggle_environments.make(\"cabt\")`.\n"
                "Confirm that your installed `kaggle-environments` build includes the `cabt` environment."
            ) from error

        agent0 = build_local_agent(replay_enabled=replay, game_id_prefix=f"local_game_{game_number:03d}_p0")
        agent1 = build_local_agent(replay_enabled=replay, game_id_prefix=f"local_game_{game_number:03d}_p1")

        print(f"[Game {game_number}/{games}] Running BaselineAgent vs BaselineAgent.")
        try:
            steps = env.run([agent0, agent1])
        except Exception as error:
            raise LocalRunnerError(
                "The official cabt environment failed while running the local match.\n"
                "Re-run with a supported `kaggle-environments` installation and check the environment error output."
            ) from error

        final_step = steps[-1]
        statuses = [state.status for state in final_step]
        rewards = [state.reward for state in final_step]
        output_path = _html_output_path(base_html_path, game_number, games)
        save_result_html(env, output_path)
        print(f"[Game {game_number}/{games}] Statuses: {statuses} | Rewards: {rewards}")
        print(f"[Game {game_number}/{games}] HTML replay written to {output_path}.")

    if replay:
        print("Replay logs written to outputs/replays/.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for official local matches."""

    parser = build_argument_parser()
    args = parser.parse_args(argv)
    try:
        return run_local_games(games=args.games, replay=args.replay, seed=args.seed, html_path=args.html)
    except LocalRunnerError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
