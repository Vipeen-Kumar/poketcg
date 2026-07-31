"""Replay and debug logging dataclasses."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(slots=True, frozen=True)
class ActionRecord:
    """Serializable description of a legal or chosen action."""

    action_type: str
    action_index: int
    description: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dictionary."""

        return asdict(self)


@dataclass(slots=True, frozen=True)
class DecisionMetadata:
    """Optional strategy metadata attached to a chosen action."""

    rule_name: str | None = None
    reason: str | None = None
    confidence: float | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dictionary."""

        return asdict(self)


@dataclass(slots=True, frozen=True)
class PokemonSnapshot:
    """Serializable Pokemon state for replay output."""

    name: str
    card_id: int
    hp: int
    max_hp: int
    damage_taken: int
    status_conditions: tuple[str, ...] = ()
    attached_energy: tuple[str, ...] = ()
    attached_energy_count: int = 0
    tools: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dictionary."""

        return asdict(self)


@dataclass(slots=True, frozen=True)
class PlayerSnapshot:
    """Serializable player board summary for one turn."""

    side: str
    active: PokemonSnapshot | None = None
    bench: tuple[PokemonSnapshot, ...] = ()
    prize_count: int = 0
    deck_count: int = 0
    hand_count: int = 0
    discard_count: int = 0

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dictionary."""

        payload = asdict(self)
        return payload


@dataclass(slots=True, frozen=True)
class TurnSnapshot:
    """Serializable snapshot of one decision point."""

    turn_number: int | None
    current_player: str | None
    game_phase: str | None
    result: str | None
    me: PlayerSnapshot | None = None
    opponent: PlayerSnapshot | None = None
    legal_actions: tuple[ActionRecord, ...] = ()
    chosen_action: ActionRecord | None = None
    decision_metadata: DecisionMetadata = field(default_factory=DecisionMetadata)
    logs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dictionary."""

        payload = asdict(self)
        return payload


@dataclass(slots=True)
class ReplaySession:
    """One complete debug replay session."""

    game_id: str
    started_at: str | None = None
    finished_at: str | None = None
    status: str = "initialized"
    turns: list[TurnSnapshot] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)
    markdown_path: Path | None = None
    json_path: Path | None = None

    def start_game(self, *, started_at: str | None = None, metadata: dict[str, object] | None = None) -> None:
        """Mark the session as started."""

        self.started_at = started_at
        self.status = "in_progress"
        if metadata:
            self.metadata.update(metadata)

    def log_turn(self, snapshot: TurnSnapshot) -> None:
        """Append one turn snapshot."""

        self.turns.append(snapshot)

    def finish(self, *, finished_at: str | None = None, metadata: dict[str, object] | None = None) -> None:
        """Mark the session as finished."""

        self.finished_at = finished_at
        self.status = "finished"
        if metadata:
            self.metadata.update(metadata)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dictionary."""

        return {
            "game_id": self.game_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status,
            "metadata": dict(self.metadata),
            "turns": [turn.to_dict() for turn in self.turns],
            "markdown_path": None if self.markdown_path is None else str(self.markdown_path),
            "json_path": None if self.json_path is None else str(self.json_path),
        }
