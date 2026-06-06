"""JSON builder for `aidash cost`. Implemented by the COST agent.

Returns the CostData payload (see ARCHITECTURE.md). The CLI wraps it via
common.envelope("cost", data, ...). Do NOT touch Rich code or other modules.
"""

from __future__ import annotations

from aidash.models import Session


def build_cost_json(
    sessions: list[Session],
    *,
    period: str,
    group_by: str | None,
    agent_filter: str | None,
) -> dict:
    """Build the CostData dict (view "detail" or "grouped")."""
    raise NotImplementedError("COST agent implements build_cost_json")
