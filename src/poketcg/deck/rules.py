"""Reusable deck-legality rules."""

from __future__ import annotations

from abc import ABC, abstractmethod

from poketcg.config import get_default_config
from poketcg.domain.enums import CardType as DomainCardType

from .models import DeckValidationContext, DeckValidationIssue


class BaseDeckValidationRule(ABC):
    """Abstract deck-legality rule."""

    name: str

    @abstractmethod
    def validate(self, context: DeckValidationContext) -> tuple[DeckValidationIssue, ...]:
        """Return the issues found by this rule."""


class DeckSizeRule(BaseDeckValidationRule):
    """Ensure the deck contains the expected number of cards."""

    name = "DeckSizeRule"

    def __init__(self, expected_size: int | None = None) -> None:
        self._expected_size = expected_size or get_default_config().environment.default_deck_size

    def validate(self, context: DeckValidationContext) -> tuple[DeckValidationIssue, ...]:
        actual = len(context.deck.card_ids)
        if actual == self._expected_size:
            return ()
        return (
            DeckValidationIssue(
                rule_name=self.name,
                message=f"Deck must contain exactly {self._expected_size} cards.",
                copies_found=actual,
                maximum_allowed=self._expected_size,
            ),
        )


class DeckCopyLimitRule(BaseDeckValidationRule):
    """Enforce standard per-card copy limits."""

    name = "DeckCopyLimitRule"

    def __init__(self, default_max_copies: int = 4) -> None:
        self._default_max_copies = default_max_copies

    def validate(self, context: DeckValidationContext) -> tuple[DeckValidationIssue, ...]:
        issues: list[DeckValidationIssue] = []
        for card_id, copies in sorted(context.counts.items()):
            card = context.resolved_cards.get(card_id)
            if card is None:
                continue
            if card.is_ace_spec():
                continue
            if card.card_type is DomainCardType.BASIC_ENERGY:
                continue
            maximum_allowed = self._default_max_copies
            if copies <= maximum_allowed:
                continue
            issues.append(
                DeckValidationIssue(
                    rule_name=self.name,
                    message=f'Card "{card.name}" exceeds the maximum copy limit.',
                    card_id=card.card_id,
                    card_name=card.name,
                    copies_found=copies,
                    maximum_allowed=maximum_allowed,
                )
            )
        return tuple(issues)


class AceSpecLimitRule(BaseDeckValidationRule):
    """Enforce the single-copy ACE SPEC deck restriction."""

    name = "AceSpecLimitRule"

    def validate(self, context: DeckValidationContext) -> tuple[DeckValidationIssue, ...]:
        issues: list[DeckValidationIssue] = []
        for card_id, copies in sorted(context.counts.items()):
            card = context.resolved_cards.get(card_id)
            if card is None or not card.is_ace_spec():
                continue
            if copies <= 1:
                continue
            issues.append(
                DeckValidationIssue(
                    rule_name=self.name,
                    message=f'ACE SPEC card "{card.name}" may appear only once.',
                    card_id=card.card_id,
                    card_name=card.name,
                    copies_found=copies,
                    maximum_allowed=1,
                )
            )
        return tuple(issues)


class UnknownCardRule(BaseDeckValidationRule):
    """Ensure every card id exists in the card database."""

    name = "UnknownCardRule"

    def validate(self, context: DeckValidationContext) -> tuple[DeckValidationIssue, ...]:
        issues: list[DeckValidationIssue] = []
        for card_id in sorted(context.counts):
            if card_id in context.resolved_cards:
                continue
            issues.append(
                DeckValidationIssue(
                    rule_name=self.name,
                    message=f"Unknown card id {card_id} in deck.",
                    card_id=card_id,
                )
            )
        return tuple(issues)
