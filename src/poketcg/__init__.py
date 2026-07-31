"""Core package for the poketcg project."""

from .config import ProjectConfig, get_default_config
from . import rules as _rules

__all__ = ["ProjectConfig", "get_default_config"]
