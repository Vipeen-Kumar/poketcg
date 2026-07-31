"""Replay formatter helpers."""

from __future__ import annotations

import json

from .models import ActionRecord, PlayerSnapshot, PokemonSnapshot, ReplaySession, TurnSnapshot


class MarkdownReplayFormatter:
    """Format replay sessions as Markdown."""

    def format_session(self, session: ReplaySession) -> str:
        """Return a Markdown document for the whole replay."""

        lines = [f"# Replay {session.game_id}", ""]
        if session.started_at is not None:
            lines.append(f"Started: {session.started_at}")
        if session.finished_at is not None:
            lines.append(f"Finished: {session.finished_at}")
        lines.extend(["", f"Status: {session.status}", ""])
        for snapshot in session.turns:
            lines.extend(self._format_turn(snapshot))
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def _format_turn(self, snapshot: TurnSnapshot) -> list[str]:
        lines = [
            "==================================================",
            f"Turn {snapshot.turn_number if snapshot.turn_number is not None else '?'}",
            "==================================================",
            "",
            f"Current Player: {snapshot.current_player or 'UNKNOWN'}",
            f"Phase: {snapshot.game_phase or 'UNKNOWN'}",
        ]
        if snapshot.result is not None:
            lines.append(f"Result: {snapshot.result}")
        lines.extend(["", "Me", ""])
        lines.extend(self._format_player(snapshot.me))
        lines.extend(["", "Opponent", ""])
        lines.extend(self._format_player(snapshot.opponent))
        lines.extend(["", "Legal Actions", ""])
        if snapshot.legal_actions:
            for index, action in enumerate(snapshot.legal_actions, start=1):
                lines.append(f"{index}. {action.description}")
        else:
            lines.append("None")
        lines.extend(["", "Chosen", ""])
        if snapshot.chosen_action is None:
            lines.append("None")
        else:
            lines.append(snapshot.chosen_action.description)
        lines.extend(["", "Reason", ""])
        lines.append(f"Rule: {snapshot.decision_metadata.rule_name or ''}")
        lines.append(f"Reason: {snapshot.decision_metadata.reason or ''}")
        if snapshot.decision_metadata.confidence is not None:
            lines.append(f"Confidence: {snapshot.decision_metadata.confidence}")
        lines.append(f"Notes: {snapshot.decision_metadata.notes or ''}")
        if snapshot.logs:
            lines.extend(["", "Logs", ""])
            lines.extend(f"- {entry}" for entry in snapshot.logs)
        if snapshot.decision_trace is not None:
            lines.extend(["", "Decision Trace", ""])
            rule_results = snapshot.decision_trace.get("rule_results", [])
            for entry in rule_results:
                status = "PASSED" if entry.get("passed") else "FAILED"
                reason = entry.get("reason") or ""
                lines.append(f"- {entry.get('rule_name', 'UnknownRule')}: {status} - {reason}")
        return lines

    def _format_player(self, player: PlayerSnapshot | None) -> list[str]:
        if player is None:
            return ["No player data"]
        lines = ["Active:"]
        lines.extend(self._format_pokemon(player.active))
        lines.extend(["", "Bench"])
        if player.bench:
            for pokemon in player.bench:
                lines.extend(self._format_pokemon(pokemon))
        else:
            lines.append("Empty")
        lines.extend(
            [
                "",
                f"Hand: {player.hand_count} cards",
                f"Deck: {player.deck_count}",
                f"Prizes: {player.prize_count}",
                f"Discard: {player.discard_count}",
            ]
        )
        return lines

    def _format_pokemon(self, pokemon: PokemonSnapshot | None) -> list[str]:
        if pokemon is None:
            return ["None"]
        return [
            pokemon.name,
            f"HP {pokemon.hp}/{pokemon.max_hp}",
            f"Damage {pokemon.damage_taken}",
            f"Status: {', '.join(pokemon.status_conditions) if pokemon.status_conditions else 'None'}",
            f"Energy: {pokemon.attached_energy_count}",
            f"Tools: {', '.join(pokemon.tools) if pokemon.tools else 'None'}",
        ]


class JsonReplayFormatter:
    """Format replay sessions as JSON."""

    def format_session(self, session: ReplaySession) -> str:
        """Return a JSON document for the whole replay."""

        return json.dumps(session.to_dict(), indent=2, sort_keys=True)
