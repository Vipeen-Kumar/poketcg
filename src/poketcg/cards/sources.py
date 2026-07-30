"""Concrete data sources for card metadata."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Final

from .interfaces import BaseCardDataSource


class CsvCardDataSource(BaseCardDataSource):
    """CSV-backed card-data source."""

    REQUIRED_COLUMNS: Final[tuple[str, ...]] = (
        "Card ID",
        "Card Name",
        "Expansion",
        "Collection No.",
        "Stage (Pokémon)/Type (Energy and Trainer)",
        "Rule",
        "Category",
        "Previous stage",
        "HP",
        "Type",
        "Weakness",
        "Resistance (Type)",
        "Retreat",
        "Move Name",
        "Cost",
        "Damage",
        "Effect Explanation",
    )

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        """Return the underlying CSV path."""

        return self._path

    def load_rows(self) -> list[dict[str, str]]:
        """Load CSV rows into dictionaries."""

        with self._path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ValueError(f"CSV file has no header: {self._path}")
            missing_columns = [column for column in self.REQUIRED_COLUMNS if column not in reader.fieldnames]
            if missing_columns:
                missing = ", ".join(missing_columns)
                raise ValueError(f"CSV file is missing required columns: {missing}")
            return [dict(row) for row in reader]
