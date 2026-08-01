"""Action-layer enumerations."""

from __future__ import annotations

from enum import Enum, auto


class ActionKind(Enum):
    PLAY_CARD = auto()
    ATTACH_ENERGY = auto()
    EVOLVE = auto()
    USE_ABILITY = auto()
    RETREAT = auto()
    ATTACK = auto()
    END_TURN = auto()
    CHOOSE_CARD = auto()
    CHOOSE_ENERGY = auto()
    CHOOSE_NUMBER = auto()
    CHOOSE_BOOLEAN = auto()
    CHOOSE_SPECIAL_CONDITION = auto()
    CHOOSE_SKILL = auto()
    UNKNOWN = auto()
