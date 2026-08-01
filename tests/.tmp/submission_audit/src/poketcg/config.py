"""Project configuration models and defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PACKAGE_ROOT.parent
PROJECT_ROOT = SRC_ROOT.parent
DATA_DIR = PROJECT_ROOT / "data"
DOCS_DIR = PROJECT_ROOT / "docs"
TESTS_DIR = PROJECT_ROOT / "tests"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"


@dataclass(slots=True, frozen=True)
class PathsConfig:
    """Filesystem paths used across the project."""

    project_root: Path = PROJECT_ROOT
    src_root: Path = SRC_ROOT
    package_root: Path = PACKAGE_ROOT
    data_dir: Path = DATA_DIR
    docs_dir: Path = DOCS_DIR
    tests_dir: Path = TESTS_DIR
    outputs_dir: Path = OUTPUTS_DIR
    raw_data_dir: Path = DATA_DIR / "raw"
    processed_data_dir: Path = DATA_DIR / "processed"
    replay_outputs_dir: Path = OUTPUTS_DIR / "replays"
    environment_doc: Path = DOCS_DIR / "environment.md"
    architecture_doc: Path = DOCS_DIR / "architecture.md"
    english_card_csv: Path = PROJECT_ROOT / "EN_Card_Data.csv"
    japanese_card_csv: Path = PROJECT_ROOT / "JP_Card_Data.csv"


@dataclass(slots=True, frozen=True)
class EnvironmentConfig:
    """Runtime settings related to the Kaggle/cabt environment boundary."""

    environment_name: str = "cabt"
    max_players: int = 2
    default_deck_size: int = 60
    default_bench_size: int = 5
    default_prize_count: int = 6
    submission_entrypoint: str = "main.py"
    submission_deck_file: str = "deck.csv"


@dataclass(slots=True, frozen=True)
class RuntimeConfig:
    """Generic application runtime settings."""

    random_seed: int = 7
    log_level: str = "INFO"
    enable_structured_logging: bool = False
    timezone_name: str = "Asia/Calcutta"


@dataclass(slots=True, frozen=True)
class TrainingConfig:
    """Reserved settings for future training workflows."""

    experiment_dir_name: str = "experiments"
    checkpoint_dir_name: str = "checkpoints"
    replay_dir_name: str = "replays"
    metrics_dir_name: str = "metrics"
    default_batch_size: int = 0
    default_num_workers: int = 0


@dataclass(slots=True, frozen=True)
class ReplayLoggingConfig:
    """Runtime settings for development-only replay logging."""

    enabled: bool = False
    output_directory: Path = OUTPUTS_DIR / "replays"
    write_markdown: bool = True
    write_json: bool = True
    maximum_saved_games: int = 100
    compression: str | None = None


@dataclass(slots=True, frozen=True)
class ProjectConfig:
    """Top-level project configuration object."""

    paths: PathsConfig = field(default_factory=PathsConfig)
    environment: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    replay_logging: ReplayLoggingConfig = field(default_factory=ReplayLoggingConfig)


def get_default_config() -> ProjectConfig:
    """Return the default project configuration."""

    return ProjectConfig()
