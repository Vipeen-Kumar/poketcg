"""Pokémon rule library."""

from .ability import AbilityRule
from .attack import AttackRule
from .base import BaseRule
from .end_turn import EndTurnRule
from .energy import AttachEnergyRule
from .evolution import EvolutionRule
from .fallback import FallbackRule
from .item import ItemRule
from .knockout import KnockoutRule
from .prize import PrizeRule
from .registry import DEFAULT_RULE_REGISTRY, RuleRegistry, get_default_registry, register_default_rule
from .retreat import RetreatRule
from .stadium import StadiumRule
from .supporter import SupporterRule
from .winning_attack import WinningAttackRule

__all__ = [
    "AbilityRule",
    "AttachEnergyRule",
    "AttackRule",
    "BaseRule",
    "DEFAULT_RULE_REGISTRY",
    "EndTurnRule",
    "EvolutionRule",
    "FallbackRule",
    "ItemRule",
    "KnockoutRule",
    "PrizeRule",
    "RetreatRule",
    "RuleRegistry",
    "StadiumRule",
    "SupporterRule",
    "WinningAttackRule",
    "get_default_registry",
    "register_default_rule",
]
