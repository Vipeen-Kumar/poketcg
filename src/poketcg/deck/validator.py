"""Composable deck validator."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence

from poketcg.cards import CardDatabase
from poketcg.domain import Deck

from .exceptions import DeckValidationError
from .models import DeckValidationContext, DeckValidationIssue, DeckValidationResult
from .rules import AceSpecLimitRule, BaseDeckValidationRule, DeckCopyLimitRule, DeckSizeRule, UnknownCardRule


class DeckValidator:
    """Validate decks using a small set of composable rules."""

    def __init__(
        self,
        card_database: CardDatabase,
        rules: Sequence[BaseDeckValidationRule] | None = None,
    ) -> None:
        self._card_database = card_database
        self._rules = tuple(rules or (UnknownCardRule(), DeckSizeRule(), AceSpecLimitRule(), DeckCopyLimitRule()))

    def validate(self, deck: Deck) -> DeckValidationResult:
        """Validate a deck and return the collected issues."""

        context = self._build_context(deck)
        issues: list[DeckValidationIssue] = []
        for rule in self._rules:
            issues.extend(rule.validate(context))
        return DeckValidationResult(deck=deck, issues=tuple(issues))

    def validate_or_raise(self, deck: Deck) -> DeckValidationResult:
        """Validate a deck and raise if any issues are found."""

        result = self.validate(deck)
        if not result.is_valid:
            raise DeckValidationError(self._format_message(result.issues), issues=result.issues)
        return result

    def _build_context(self, deck: Deck) -> DeckValidationContext:
        counts = Counter(deck.card_ids)
        resolved_cards = {}
        for card_id in counts:
            if self._card_database.exists(card_id):
                resolved_cards[card_id] = self._card_database.get(card_id)
        return DeckValidationContext(
            deck=deck,
            card_database=self._card_database,
            resolved_cards=resolved_cards,
            counts=dict(counts),
        )

    def _format_message(self, issues: Iterable[DeckValidationIssue]) -> str:
        lines = ["Deck validation failed:"]
        for issue in issues:
            details = issue.message
            if issue.card_id is not None:
                details += f" Card ID: {issue.card_id}."
            if issue.copies_found is not None:
                details += f" Copies found: {issue.copies_found}."
            if issue.maximum_allowed is not None:
                details += f" Maximum allowed: {issue.maximum_allowed}."
            lines.append(f"- {details}")
        return "\n".join(lines)

