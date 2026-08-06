"""Context information for selection resolution."""

from dataclasses import dataclass

from poketcg.domain import GameState, SelectPrompt


@dataclass(slots=True, frozen=True)
class SelectionContext:
    """Context needed to resolve a selection."""

    selection: SelectPrompt
    game_state: GameState | None = None
