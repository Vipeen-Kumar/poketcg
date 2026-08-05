"""Official kaggle-environments local runner for the baseline submission agent."""

from __future__ import annotations

import argparse
import inspect
import importlib
import sys
import traceback
from pathlib import Path
from pprint import pformat
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from main import create_submission_agent
from poketcg.cards import CardDatabase
from poketcg.agent import BaselineAgentConfig, create_baseline_agent
from poketcg.deck import DeckLoader
from poketcg.debug.replay_logger import ReplayLoggerConfig


class LocalRunnerError(RuntimeError):
    """Raised when the local Kaggle runner cannot be started."""


class DiagnosticAgentWrapper:
    """Thin diagnostic wrapper that records the last observation and callback stage."""

    def __init__(self, agent, *, name: str) -> None:
        self._agent = agent
        self.name = name
        self.last_observation: object | None = None
        self.last_callback: str | None = None
        self._agent_signature = None
        if callable(agent):
            try:
                self._agent_signature = inspect.signature(agent)
            except (TypeError, ValueError):
                self._agent_signature = None
        self._instrument_agent()

    def _instrument_agent(self) -> None:
        self._wrap_method(self._agent, "select_deck", callback_name="deck selection")

        parser = getattr(self._agent, "_observation_parser", None)
        if parser is not None:
            self._wrap_method(parser, "parse", callback_name="observation parsing")

        decision_engine = getattr(self._agent, "_decision_engine", None)
        if decision_engine is not None:
            self._wrap_method(decision_engine, "decide", callback_name="action selection")

        replay_logger = getattr(self._agent, "_replay_logger", None)
        if replay_logger is not None:
            for method_name in ("start_game", "log_turn", "log_action", "finish"):
                self._wrap_method(replay_logger, method_name, callback_name="replay logger")

    def _wrap_method(self, target: object, method_name: str, *, callback_name: str) -> None:
        original = getattr(target, method_name, None)
        if original is None or not callable(original):
            return

        def wrapped(*args, **kwargs):
            self.last_callback = callback_name
            try:
                return original(*args, **kwargs)
            except Exception:
                _print_failure_banner(f"{self.name}: {callback_name}")
                _print_traceback()
                _print_last_observation(self.last_observation, self.name)
                raise

        setattr(target, method_name, wrapped)

    def __call__(self, *args, **kwargs) -> object:
        observation = args[0] if args else kwargs.get("observation")
        self.last_observation = observation
        self.last_callback = "deck selection" if _is_deck_selection_payload(observation) else "action selection"
        try:
            return self._invoke_agent(*args, **kwargs)
        except Exception:
            _print_failure_banner(f"{self.name}: agent callback")
            _print_traceback()
            _print_last_observation(self.last_observation, self.name)
            raise

    def _invoke_agent(self, *args, **kwargs) -> object:
        if not callable(self._agent):
            return self._agent
        if self._agent_signature is not None:
            try:
                self._agent_signature.bind(*args, **kwargs)
            except TypeError:
                observation = args[0] if args else kwargs.get("observation")
                return self._agent(observation)
        return self._agent(*args, **kwargs)


def _is_deck_selection_payload(observation: object) -> bool:
    if not isinstance(observation, dict):
        return False
    
    # Check if observation is wrapped in "observation" key (Kaggle format)
    observation_data = observation
    if "observation" in observation and isinstance(observation["observation"], dict):
        observation_data = observation["observation"]
    
    return observation_data.get("current") is None and observation_data.get("select") is None


def _print_failure_banner(callback_name: str) -> None:
    print(f"[Diagnostic] Callback failed: {callback_name}", file=sys.stderr)


def _print_traceback() -> None:
    print("[Diagnostic] Python traceback follows:", file=sys.stderr)
    traceback.print_exc()


def _print_last_observation(observation: object, agent_name: str) -> None:
    print(f"[Diagnostic] Last observation passed to {agent_name}:", file=sys.stderr)
    print(pformat(observation, width=120), file=sys.stderr)


def _print_environment_details(env: object) -> None:
    state = getattr(env, "state", None)
    logs = getattr(env, "logs", None)
    if state is not None:
        print("[Diagnostic] env.state:", file=sys.stderr)
        print(pformat(state, width=120), file=sys.stderr)
    if logs is not None:
        print("[Diagnostic] env.logs:", file=sys.stderr)
        print(pformat(logs, width=120), file=sys.stderr)


def _print_all_agent_observations(agents: Sequence[DiagnosticAgentWrapper]) -> None:
    for agent in agents:
        print(
            f"[Diagnostic] {agent.name} last callback: {agent.last_callback}",
            file=sys.stderr,
        )
        _print_last_observation(agent.last_observation, agent.name)


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
    card_database = CardDatabase()
    card_database.load()
    loader = DeckLoader(card_database)
    deck = loader.load(deck_path)
    return list(deck.card_ids)


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
        except Exception:
            _print_failure_banner("environment creation")
            _print_traceback()
            raise

        agent0 = DiagnosticAgentWrapper(
            build_local_agent(replay_enabled=replay, game_id_prefix=f"local_game_{game_number:03d}_p0"),
            name="agent0",
        )
        agent1 = DiagnosticAgentWrapper(
            build_local_agent(replay_enabled=replay, game_id_prefix=f"local_game_{game_number:03d}_p1"),
            name="agent1",
        )
        agents = (agent0, agent1)

        print(f"[Game {game_number}/{games}] Running BaselineAgent vs BaselineAgent.")
        try:
            steps = env.run([agent0, agent1])
        except Exception:
            _print_failure_banner("environment step")
            _print_traceback()
            _print_environment_details(env)
            _print_all_agent_observations(agents)
            raise

        final_step = steps[-1]
        statuses = [state.status for state in final_step]
        rewards = [state.reward for state in final_step]
        output_path = _html_output_path(base_html_path, game_number, games)
        try:
            save_result_html(env, output_path)
        except Exception:
            _print_failure_banner("environment step")
            _print_traceback()
            _print_environment_details(env)
            _print_all_agent_observations(agents)
            raise
        print(f"[Game {game_number}/{games}] Statuses: {statuses} | Rewards: {rewards}")
        print(f"[Game {game_number}/{games}] HTML replay written to {output_path}.")

    if replay:
        print("Replay logs written to outputs/replays/.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for official local matches."""

    parser = build_argument_parser()
    args = parser.parse_args(argv)
    return run_local_games(games=args.games, replay=args.replay, seed=args.seed, html_path=args.html)


if __name__ == "__main__":
    raise SystemExit(main())
