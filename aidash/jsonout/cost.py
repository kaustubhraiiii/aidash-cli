"""JSON builder for `aidash cost`. Implemented by the COST agent.

Returns the CostData payload (see ARCHITECTURE.md). The CLI wraps it via
common.envelope("cost", data, ...). Do NOT touch Rich code or other modules.
"""

from __future__ import annotations

from aidash.models import Session

from .common import (
    agent_label,
    build_empty_state,
    build_session_tokens,
    build_tokens_for_sessions,
    fmt_date,
    fmt_money,
    iso_or_none,
    session_cost,
    short_id,
)


def _build_totals(sessions: list[Session]) -> dict:
    cost_usd = sum(session_cost(s) for s in sessions)
    return {
        "session_count": len(sessions),
        "tokens": build_tokens_for_sessions(sessions),
        "cost_usd": cost_usd,
        "cost_display": fmt_money(cost_usd, 4),
    }


def _detail_rows(sessions: list[Session]) -> list[dict]:
    rows: list[dict] = []
    for s in sessions:
        cost_usd = session_cost(s)
        rows.append(
            {
                "session_id": s.id,
                "session_id_short": short_id(s.id),
                "date": iso_or_none(s.start_time),
                "date_display": fmt_date(s.start_time),
                "agent": s.agent,
                "agent_label": agent_label(s.agent),
                "project": s.project or "",
                "model": s.model or "",
                "tokens": build_session_tokens(s),
                "cost_usd": cost_usd,
                "cost_display": fmt_money(cost_usd, 4),
            }
        )
    return rows


def _grouped_rows(sessions: list[Session], group_by: str) -> list[dict]:
    groups: dict[str, list[Session]] = {}
    for s in sessions:
        key = getattr(s, group_by, "") or ""
        groups.setdefault(key, []).append(s)

    rows: list[dict] = []
    for key, group_sessions in groups.items():
        cost_usd = sum(session_cost(s) for s in group_sessions)
        if group_by == "agent":
            key_label = agent_label(key)
        else:
            key_label = key or ""
        rows.append(
            {
                "key": key,
                "key_label": key_label,
                "session_count": len(group_sessions),
                "tokens": build_tokens_for_sessions(group_sessions),
                "cost_usd": cost_usd,
                "cost_display": fmt_money(cost_usd, 4),
            }
        )

    rows.sort(key=lambda r: r["cost_usd"], reverse=True)
    return rows


def build_cost_json(
    sessions: list[Session],
    *,
    period: str,
    group_by: str | None,
    agent_filter: str | None,
) -> dict:
    """Build the CostData dict (view "detail" or "grouped")."""
    view = "grouped" if group_by else "detail"

    if group_by:
        rows = _grouped_rows(sessions, group_by)
    else:
        rows = _detail_rows(sessions)

    empty = None
    if not sessions:
        empty = build_empty_state(
            {"period": period, "agent": agent_filter, "by": group_by},
            "Try removing filters or expanding --period.",
        )

    return {
        "view": view,
        "period": period,
        "group_by": group_by,
        "rows": rows,
        "totals": _build_totals(sessions),
        "empty": empty,
        "export": None,
        "markdown": None,
    }
