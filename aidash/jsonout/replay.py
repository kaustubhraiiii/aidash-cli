"""JSON builder for `aidash replay`. Implemented by the REPLAY agent.

Returns the ReplayData payload (see ARCHITECTURE.md). The CLI wraps it via
common.envelope("replay", data, ...). Do NOT touch Rich code or other modules.
"""

from __future__ import annotations

from aidash.models import Session


def build_replay_json(sessions: list[Session], *, target: str) -> dict:
    """Build the ReplayData dict for target = last | today | <id substring>.

    `sessions` is already period-scoped by the CLI (today is pre-filtered);
    select within it: last -> first session, today -> all, else id substring.
    """
    raise NotImplementedError("REPLAY agent implements build_replay_json")
