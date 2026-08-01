"""Card metadata package."""

from .database import CardDatabase
from .interfaces import BaseCardCatalog, BaseCardDataCache, BaseCardDataSource
from .models import (
    AbilityData,
    AttackData,
    CardData,
    EnergyCost,
    EvolutionData,
    ResistanceData,
    RetreatCost,
    WeaknessData,
)
from .statistics import CardDatabaseStats, build_card_database_stats

__all__ = [
    "AbilityData",
    "AttackData",
    "BaseCardCatalog",
    "BaseCardDataCache",
    "BaseCardDataSource",
    "CardData",
    "CardDatabase",
    "CardDatabaseStats",
    "EnergyCost",
    "EvolutionData",
    "ResistanceData",
    "RetreatCost",
    "WeaknessData",
    "build_card_database_stats",
]
