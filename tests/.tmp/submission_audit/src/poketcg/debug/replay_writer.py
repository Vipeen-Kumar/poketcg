"""Replay output persistence helpers."""

from __future__ import annotations

from pathlib import Path

from .formatter import JsonReplayFormatter, MarkdownReplayFormatter
from .models import ReplaySession


class ReplayWriter:
    """Write replay sessions to disk."""

    def __init__(
        self,
        *,
        output_directory: Path,
        write_markdown: bool = True,
        write_json: bool = True,
        maximum_saved_games: int = 100,
        compression: str | None = None,
        markdown_formatter: MarkdownReplayFormatter | None = None,
        json_formatter: JsonReplayFormatter | None = None,
    ) -> None:
        self._output_directory = output_directory
        self._write_markdown = write_markdown
        self._write_json = write_json
        self._maximum_saved_games = maximum_saved_games
        self._compression = compression
        self._markdown_formatter = markdown_formatter or MarkdownReplayFormatter()
        self._json_formatter = json_formatter or JsonReplayFormatter()

    def write(self, session: ReplaySession) -> ReplaySession:
        """Persist a replay session according to the configured formats."""

        self._output_directory.mkdir(parents=True, exist_ok=True)
        if self._write_markdown:
            markdown_path = self._output_directory / f"{session.game_id}.md"
            markdown_path.write_text(self._markdown_formatter.format_session(session), encoding="utf-8")
            session.markdown_path = markdown_path
        if self._write_json:
            json_path = self._output_directory / f"{session.game_id}.json"
            json_path.write_text(self._json_formatter.format_session(session), encoding="utf-8")
            session.json_path = json_path
        self._prune_old_replays()
        return session

    def _prune_old_replays(self) -> None:
        if self._maximum_saved_games <= 0:
            return
        replay_files = sorted(
            self._output_directory.glob("*"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        keep = self._maximum_saved_games * max(int(self._write_markdown) + int(self._write_json), 1)
        for path in replay_files[keep:]:
            if path.is_file():
                path.unlink()
