"""File helper placeholders."""

from __future__ import annotations

from pathlib import Path


def ensure_parent_dir(path: Path) -> Path:
    """Ensure a path's parent directory exists."""

    path.parent.mkdir(parents=True, exist_ok=True)
    return path
