"""Build a Kaggle-compatible submission.tar.gz bundle."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from main import create_submission_agent


class SubmissionBuildError(RuntimeError):
    """Raised when the submission bundle cannot be created safely."""


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the submission-builder CLI."""

    parser = argparse.ArgumentParser(description="Build a Kaggle submission.tar.gz bundle.")
    parser.add_argument("--output", default="submission.tar.gz", help="Output archive path.")
    parser.add_argument("--run-tests", action="store_true", help="Run the unittest suite before packaging.")
    return parser


def load_deck_csv(path: Path) -> list[int]:
    """Load and validate a submission deck file."""

    if not path.exists():
        raise SubmissionBuildError(f"Missing required submission file: {path}")

    deck: list[int] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        try:
            deck.append(int(stripped))
        except ValueError as error:
            raise SubmissionBuildError(f"Invalid deck.csv value on line {line_number}: {stripped!r}") from error

    if len(deck) != 60:
        raise SubmissionBuildError(f"deck.csv must contain exactly 60 card ids; found {len(deck)}.")
    return deck


def verify_submission_inputs() -> dict[str, Path]:
    """Validate the runtime files required by the current implementation."""

    files = {
        "main": PROJECT_ROOT / "main.py",
        "deck": PROJECT_ROOT / "deck.csv",
        "cards": PROJECT_ROOT / "EN_Card_Data.csv",
        "package": PROJECT_ROOT / "src" / "poketcg",
    }
    for label, path in files.items():
        if not path.exists():
            raise SubmissionBuildError(f"Missing required runtime path for {label}: {path}")

    deck = load_deck_csv(files["deck"])
    expected_deck = list(create_submission_agent().select_deck().card_ids)
    if deck != expected_deck:
        raise SubmissionBuildError("deck.csv does not match the BaselineAgent submission deck.")

    return files


def run_tests() -> None:
    """Run the required unit-test suite before packaging."""

    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", '-p', "test_*.py", "-v"],
        cwd=PROJECT_ROOT,
        check=False,
    )
    if result.returncode != 0:
        raise SubmissionBuildError("Unit tests failed; refusing to build submission archive.")


def build_archive(output_path: Path, files: dict[str, Path]) -> Path:
    """Create the submission archive with only runtime files."""

    runtime_dirs = (
        "actions",
        "agent",
        "analysis",
        "cards",
        "debug",
        "decision",
        "domain",
        "engine",
        "rules",
        "shared",
        "utils",
    )
    runtime_files = (
        files["package"] / "__init__.py",
        files["package"] / "config.py",
        files["package"] / "py.typed",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output_path, "w:gz") as archive:
        archive.add(files["main"], arcname="main.py")
        archive.add(files["deck"], arcname="deck.csv")
        archive.add(files["cards"], arcname="EN_Card_Data.csv")
        for source_path in runtime_files:
            archive.add(source_path, arcname=str(source_path.relative_to(PROJECT_ROOT)))
        for runtime_dir in runtime_dirs:
            for source_path in sorted((files["package"] / runtime_dir).rglob("*")):
                if source_path.is_dir():
                    continue
                if "__pycache__" in source_path.parts:
                    continue
                if source_path.suffix == ".pyc":
                    continue
                if source_path.name == "README.md":
                    continue
                archive.add(source_path, arcname=str(source_path.relative_to(PROJECT_ROOT)))
    return output_path


def verify_archive(output_path: Path) -> list[str]:
    """Return archive members after validating Kaggle-required root files."""

    with tarfile.open(output_path, "r:gz") as archive:
        members = sorted(member.name for member in archive.getmembers() if member.isfile())

    root_files = {name for name in members if "/" not in name}
    required_root = {"main.py", "deck.csv"}
    if not required_root.issubset(root_files):
        raise SubmissionBuildError(
            f"Archive is missing Kaggle-required root files. Found root files: {sorted(root_files)}"
        )
    return members


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for submission packaging."""

    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        files = verify_submission_inputs()
        if args.run_tests:
            run_tests()
        output_path = build_archive(Path(args.output), files)
        members = verify_archive(output_path)
    except SubmissionBuildError as error:
        print(str(error), file=sys.stderr)
        return 1

    print(f"Submission archive created: {output_path}")
    print("Archive members:")
    for member in members:
        print(f"  {member}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
