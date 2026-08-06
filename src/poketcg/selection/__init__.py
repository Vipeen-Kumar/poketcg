"""Selection resolution system for converting actions to SDK indices."""

from .registry import SelectionResolverRegistry
from .resolver import SelectionResolver

__all__ = [
    "SelectionResolver",
    "SelectionResolverRegistry",
]
