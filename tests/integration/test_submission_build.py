"""Tests for submission packaging."""

from __future__ import annotations

import importlib.util
import sys
import tarfile
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


class SubmissionBuildTestCase(unittest.TestCase):
    """Verify the repository can build a Kaggle submission archive."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_module("build_submission_module", PROJECT_ROOT / "build_submission.py")

    def test_archive_contains_required_root_files(self) -> None:
        output_path = PROJECT_ROOT / "submission_test.tar.gz"
        if output_path.exists():
            output_path.unlink()

        try:
            exit_code = self.module.main(["--output", str(output_path)])
            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())

            with tarfile.open(output_path, "r:gz") as archive:
                members = sorted(member.name for member in archive.getmembers() if member.isfile())

            self.assertIn("main.py", members)
            self.assertIn("deck.csv", members)
            self.assertIn("EN_Card_Data.csv", members)
            self.assertIn("src/poketcg/agent/baseline.py", members)
            self.assertNotIn("src/poketcg/__pycache__/__init__.cpython-313.pyc", members)
            self.assertNotIn("src/poketcg/search/interfaces.py", members)
        finally:
            output_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
