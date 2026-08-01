"""Tests for repository-level execution entrypoints."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

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


class SubmissionEntrypointTestCase(unittest.TestCase):
    """Verify the root Kaggle entrypoint stays importable and callable."""

    def test_main_module_imports_and_exposes_agent(self) -> None:
        module = _load_module("submission_main", PROJECT_ROOT / "main.py")

        self.assertTrue(callable(module.agent))
        response = module.agent({"logs": [], "current": None, "select": None})
        self.assertEqual(len(response), 60)

    def test_main_self_check_returns_success(self) -> None:
        module = _load_module("submission_main_self_check", PROJECT_ROOT / "main.py")

        self.assertEqual(module.main(), 0)


if __name__ == "__main__":
    unittest.main()
