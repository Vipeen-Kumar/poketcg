"""Replay logger entrypoint."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from poketcg.actions import ActionFactory, ActionKind, BaseAction
from poketcg.analysis import GameAnalyzer
from poketcg.config import ReplayLoggingConfig
from poketcg.domain import Observation, Player, Pokemon, PlayerSide

from .models import ActionRecord, DecisionMetadata, PlayerSnapshot, PokemonSnapshot, ReplaySession, TurnSnapshot
from .replay_writer import ReplayWriter


@dataclass(slots=True, frozen=True)
class ReplayLoggerConfig:
    """Replay logger runtime configuration."""

    enabled: bool = False
    output_directory: Path = Path("outputs/replays")
    markdown: bool = True
    json: bool = True
    maximum_saved_games: int = 100
    compression: str | None = None

    @classmethod
    def from_project_config(cls, config: ReplayLoggingConfig) -> "ReplayLoggerConfig":
        """Build logger config from the shared project config."""

        return cls(
            enabled=config.enabled,
            output_directory=config.output_directory,
            markdown=config.write_markdown,
            json=config.write_json,
            maximum_saved_games=config.maximum_saved_games,
            compression=config.compression,
        )


class ReplayLogger:
    """Development-only flight recorder for one game session."""

    def __init__(
        self,
        config: ReplayLoggerConfig | None = None,
        *,
        action_factory: ActionFactory | None = None,
        writer: ReplayWriter | None = None,
    ) -> None:
        self._config = config or ReplayLoggerConfig()
        self._action_factory = action_factory or ActionFactory()
        self._writer = writer or ReplayWriter(
            output_directory=self._config.output_directory,
            write_markdown=self._config.markdown,
            write_json=self._config.json,
            maximum_saved_games=self._config.maximum_saved_games,
            compression=self._config.compression,
        )
        self._session: ReplaySession | None = None

    @property
    def enabled(self) -> bool:
        """Return whether replay logging is enabled."""

        return self._config.enabled

    @property
    def session(self) -> ReplaySession | None:
        """Return the current replay session."""

        return self._session

    def start_game(self, game_id: str, *, metadata: dict[str, object] | None = None) -> ReplaySession | None:
        """Start a new replay session."""

        if not self.enabled:
            return None
        session = ReplaySession(game_id=game_id)
        session.start_game(started_at=self._timestamp(), metadata=metadata)
        self._session = session
        return session

    def log_turn(
        self,
        observation: Observation,
        *,
        chosen_action: BaseAction | None = None,
        decision_metadata: DecisionMetadata | None = None,
        analyzer: GameAnalyzer | None = None,
    ) -> TurnSnapshot | None:
        """Capture one decision-point snapshot."""

        if not self.enabled or self._session is None:
            return None
        resolved_analyzer = analyzer or GameAnalyzer(observation, action_factory=self._action_factory)
        legal_actions = tuple(self._action_to_record(action) for action in resolved_analyzer.actions())
        snapshot = TurnSnapshot(
            turn_number=resolved_analyzer.current_turn(),
            current_player=self._enum_name(resolved_analyzer.current_player()),
            game_phase=None if observation.state is None else observation.state.phase.name,
            result=self._enum_name(observation.result),
            me=self._player_snapshot(resolved_analyzer.me()),
            opponent=self._player_snapshot(resolved_analyzer.opponent()),
            legal_actions=legal_actions,
            chosen_action=None if chosen_action is None else self._action_to_record(chosen_action),
            decision_metadata=decision_metadata or DecisionMetadata(),
            logs=tuple(entry.event_name for entry in observation.logs),
        )
        self._session.log_turn(snapshot)
        return snapshot

    def log_action(
        self,
        chosen_action: BaseAction,
        *,
        decision_metadata: DecisionMetadata | None = None,
    ) -> TurnSnapshot | None:
        """Update the most recent snapshot with chosen-action metadata."""

        if not self.enabled or self._session is None or not self._session.turns:
            return None
        previous = self._session.turns[-1]
        updated = TurnSnapshot(
            turn_number=previous.turn_number,
            current_player=previous.current_player,
            game_phase=previous.game_phase,
            result=previous.result,
            me=previous.me,
            opponent=previous.opponent,
            legal_actions=previous.legal_actions,
            chosen_action=self._action_to_record(chosen_action),
            decision_metadata=decision_metadata or previous.decision_metadata,
            logs=previous.logs,
        )
        self._session.turns[-1] = updated
        return updated

    def finish(self, *, metadata: dict[str, object] | None = None) -> ReplaySession | None:
        """Finish and write the replay session."""

        if not self.enabled or self._session is None:
            return None
        self._session.finish(finished_at=self._timestamp(), metadata=metadata)
        return self._writer.write(self._session)

    def _action_to_record(self, action: BaseAction) -> ActionRecord:
        description = self._action_description(action)
        return ActionRecord(
            action_type=action.kind.name,
            action_index=action.action_index,
            description=description,
        )

    def _action_description(self, action: BaseAction) -> str:
        if action.kind is ActionKind.END_TURN:
            return "End Turn"
        if hasattr(action, "attack_name") and getattr(action, "attack_name") is not None:
            return f"Attack #{action.action_index}: {getattr(action, 'attack_name')}"
        if hasattr(action, "card") and getattr(action, "card") is not None:
            card = getattr(action, "card")
            return f"{action.kind.name.title().replace('_', ' ')} #{action.action_index}: {card.name}"
        if hasattr(action, "evolution_card") and getattr(action, "evolution_card") is not None:
            card = getattr(action, "evolution_card")
            return f"Evolve #{action.action_index}: {card.name}"
        return f"{action.kind.name.title().replace('_', ' ')} #{action.action_index}"

    def _player_snapshot(self, player: Player | None) -> PlayerSnapshot | None:
        if player is None:
            return None
        bench = tuple(self._pokemon_snapshot(pokemon) for pokemon in player.bench.pokemon if pokemon is not None)
        return PlayerSnapshot(
            side=player.side.name,
            active=self._pokemon_snapshot(player.active),
            bench=bench,
            prize_count=player.prizes.remaining,
            deck_count=player.deck_count,
            hand_count=player.hand_count,
            discard_count=len(player.discard),
        )

    def _pokemon_snapshot(self, pokemon: Pokemon | None) -> PokemonSnapshot | None:
        if pokemon is None:
            return None
        status_conditions = tuple(condition.name for condition in pokemon.special_conditions)
        energy = tuple(energy.name for energy in pokemon.attached_energy_types)
        tools = tuple(card.name for card in pokemon.attached_tools)
        return PokemonSnapshot(
            name=pokemon.name,
            card_id=pokemon.card_id,
            hp=pokemon.current_hp,
            max_hp=pokemon.max_hp,
            damage_taken=max(pokemon.max_hp - pokemon.current_hp, 0),
            status_conditions=status_conditions,
            attached_energy=energy,
            attached_energy_count=max(len(pokemon.attached_energy_cards), len(pokemon.attached_energy_types)),
            tools=tools,
        )

    def _enum_name(self, value: object) -> str | None:
        if value is None:
            return None
        name = getattr(value, "name", None)
        if isinstance(name, str):
            return name
        return str(value)

    def _timestamp(self) -> str:
        return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
