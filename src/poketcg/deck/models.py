"""Deck validation data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from poketcg.cards import CardDatabase
    from poketcg.cards.models import CardData
    from poketcg.domain import Deck


@dataclass(slots=True, frozen=True)
class DeckValidationIssue:
    """A single deck-legality problem detected by the validator."""

    rule_name: str
    message: str
    card_id: int | None = None
    card_name: str | None = None
    copies_found: int | None = None
    maximum_allowed: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class DeckValidationContext:
    """Shared data passed to every deck-validation rule."""

    deck: "Deck"
    card_database: "CardDatabase"
    resolved_cards: dict[int, "CardData"]
    counts: dict[int, int]


@dataclass(slots=True, frozen=True)
class DeckValidationResult:
    """Result of validating one deck."""

    deck: "Deck"
    issues: tuple[DeckValidationIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        """Return whether the deck passed every validation rule."""

        return not self.issues

