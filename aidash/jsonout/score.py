"""JSON builder for `aidash score`. Implemented by the SCORE agent.

Returns the ScoreData payload (see ARCHITECTURE.md). The CLI wraps it via
common.envelope("score", data, ...). Do NOT touch Rich code or other modules.
"""

from __future__ import annotations

from aidash.models import Session


def build_score_json(
    sessions: list[Session],
    *,
    target: str,
    trend: bool,
) -> dict:
    """Build the ScoreData dict (view "sessions" or, when trend, "trend")."""
    raise NotImplementedError("SCORE agent implements build_score_json")
