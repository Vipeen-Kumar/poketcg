"""Tests for the local execution harness."""

from __future__ import annotations

import importlib.util
import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def _load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module {module_name} from {file_path}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class FakeState:
    """Small environment state record."""

    def __init__(self, status: str, reward: int | None) -> None:
        self.status = status
        self.reward = reward


class FakeEnvironment:
    """Official-runner stand-in with run() and render()."""

    def __init__(self) -> None:
        self.run_calls: list[list[object]] = []

    def run(self, agents):
        self.run_calls.append(list(agents))
        return [[FakeState("DONE", 1), FakeState("DONE", -1)]]

    def render(self, mode: str = "html"):
        return "<html><body>fake replay</body></html>"


class LocalRunnerTestCase(unittest.TestCase):
    """Verify the repository-level local-runner behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_module("run_local_module", PROJECT_ROOT / "run_local.py")

    def test_argument_parser_supports_expected_flags(self) -> None:
        parser = self.module.build_argument_parser()

        args = parser.parse_args(["--games", "3", "--replay", "--seed", "42", "--html", "out.html"])

        self.assertEqual(args.games, 3)
        self.assertTrue(args.replay)
        self.assertEqual(args.seed, 42)
        self.assertEqual(args.html, "out.html")

    def test_missing_sdk_is_reported_cleanly(self) -> None:
        stderr = io.StringIO()
        with patch.object(
            self.module,
            "load_kaggle_make",
            side_effect=self.module.LocalRunnerError("kaggle-environments missing"),
        ):
            with redirect_stderr(stderr):
                exit_code = self.module.main([])

        self.assertEqual(exit_code, 1)
        self.assertIn("kaggle-environments missing", stderr.getvalue())

    def test_runner_completes_with_mocked_sdk(self) -> None:
        stdout = io.StringIO()
        fake_env = FakeEnvironment()
        output_path = PROJECT_ROOT / "test_result.html"
        if output_path.exists():
            output_path.unlink()
        with patch.object(self.module, "load_kaggle_make", return_value=lambda *args, **kwargs: fake_env):
            with patch.object(self.module, "create_submission_agent", side_effect=[object(), object()]):
                with patch.object(self.module, "load_deck_csv", return_value=[1] * 60):
                    with redirect_stdout(stdout):
                        exit_code = self.module.main(["--games", "1", "--html", str(output_path)])

        try:
            self.assertEqual(exit_code, 0)
            self.assertEqual(len(fake_env.run_calls), 1)
            self.assertTrue(output_path.exists())
            self.assertIn("Running BaselineAgent vs BaselineAgent.", stdout.getvalue())
            self.assertIn("HTML replay written", stdout.getvalue())
        finally:
            output_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
