"""OpenAI Codex parser."""

from pathlib import Path

from aidash.models import Session
from aidash.parsers.base import BaseParser


class CodexParser(BaseParser):
    def discover_sessions(self) -> list[Path]:
        """Discover Codex session files."""
        base = Path.home() / ".codex" / "sessions"
        if not base.exists():
            return []
        return sorted(base.rglob("*.jsonl"))

    def parse_session(self, filepath: Path) -> Session:
        """Parse a Codex session file."""
        raise NotImplementedError
