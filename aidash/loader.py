"""Unified session loader across all agents."""

from datetime import datetime, timezone
from pathlib import Path

from aidash.config import detect_agents
from aidash.models import Session
from aidash.parsers.base import BaseParser
from aidash.parsers.claude import ClaudeCodeParser
from aidash.parsers.codex import CodexParser

PARSER_MAP: dict[str, type[BaseParser]] = {
    "claude_code": ClaudeCodeParser,
    "codex": CodexParser,
}


def load_all_sessions(
    agents: list[str] | None = None,
    project: str | None = None,
    since: str | None = None,
    until: str | None = None,
) -> list[Session]:
    """Load sessions from all detected (or specified) agents.

    Args:
        agents: List of agent names to load. Auto-detects if None.
        project: Filter by project name (substring match).
        since: Include sessions starting on or after this date (YYYY-MM-DD).
        until: Include sessions starting on or before this date (YYYY-MM-DD).

    Returns:
        Flat list of Session objects sorted by start_time descending.
    """
    if agents is None:
        agents = detect_agents()

    since_dt = _parse_date(since) if since else None
    until_dt = _parse_date(until) if until else None

    all_sessions: list[Session] = []

    for agent_name in agents:
        parser_cls = PARSER_MAP.get(agent_name)
        if parser_cls is None:
            continue

        parser = parser_cls()
        filepaths = parser.discover_sessions()

        for fp in filepaths:
            try:
                session = parser.parse_session(fp)
            except Exception:
                continue

            if project and project.lower() not in (session.project or "").lower():
                continue

            if since_dt and session.start_time:
                if session.start_time.replace(tzinfo=None) < since_dt:
                    continue

            if until_dt and session.start_time:
                if session.start_time.replace(tzinfo=None) > until_dt:
                    continue

            all_sessions.append(session)

    epoch = datetime.min.replace(tzinfo=timezone.utc)
    all_sessions.sort(
        key=lambda s: (
            s.start_time.astimezone(timezone.utc) if s.start_time else epoch
        ),
        reverse=True,
    )
    return all_sessions


def _parse_date(date_str: str) -> datetime:
    """Parse a YYYY-MM-DD string into a datetime."""
    return datetime.strptime(date_str, "%Y-%m-%d")
