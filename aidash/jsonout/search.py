"""JSON builder for `aidash search`. Implemented by the SEARCH agent.

Returns the SearchData payload (see ARCHITECTURE.md). The CLI wraps it via
common.envelope("search", data, ...). Do NOT touch Rich code or other modules.
"""

from __future__ import annotations

from aidash.models import Session


def build_search_json(
    sessions: list[Session],
    *,
    query: str,
    agent_filter: str | None,
    project: str | None,
    limit: int,
) -> dict:
    """Build the SearchData dict (ranked rows with highlighted preview_segments)."""
    raise NotImplementedError("SEARCH agent implements build_search_json")
