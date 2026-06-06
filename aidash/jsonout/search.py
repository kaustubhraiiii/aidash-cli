"""JSON builder for `aidash search`. Implemented by the SEARCH agent.

Returns the SearchData payload (see ARCHITECTURE.md). The CLI wraps it via
common.envelope("search", data, ...). Do NOT touch Rich code or other modules.
"""

from __future__ import annotations

from datetime import datetime

from aidash.jsonout.common import (
    agent_label,
    build_empty_state,
    build_session_tokens,
    fmt_date,
    fmt_money,
    iso_or_none,
    session_cost,
    short_id,
)
from aidash.models import Session


def _segment_preview(text: str, query: str) -> list[dict]:
    """Split ``text`` into [{text, match}] segments around case-insensitive
    occurrences of ``query`` (mirrors cli._highlight_query, but as data)."""
    segments: list[dict] = []
    if not query:
        if text:
            segments.append({"text": text, "match": False})
        return segments

    text_lower = text.lower()
    query_lower = query.lower()
    i = 0
    while i < len(text):
        pos = text_lower.find(query_lower, i)
        if pos == -1:
            segments.append({"text": text[i:], "match": False})
            break
        if pos > i:
            segments.append({"text": text[i:pos], "match": False})
        segments.append({"text": text[pos : pos + len(query)], "match": True})
        i = pos + len(query)
    return segments


def build_search_json(
    sessions: list[Session],
    *,
    query: str,
    agent_filter: str | None,
    project: str | None,
    limit: int,
) -> dict:
    """Build the SearchData dict (ranked rows with highlighted preview_segments)."""
    query_lower = query.lower()
    scored: list[tuple[int, Session, str]] = []

    for s in sessions:
        blob_parts: list[str] = []
        for msg in s.messages:
            if msg.role == "user" and msg.content_preview:
                blob_parts.append(msg.content_preview)
            for tc in msg.tool_calls:
                blob_parts.append(tc.name)
        blob = " ".join(blob_parts).lower()
        count = blob.count(query_lower)
        if count == 0:
            continue

        first_match_preview = ""
        for msg in s.messages:
            if msg.role == "user" and msg.content_preview:
                if query_lower in msg.content_preview.lower():
                    first_match_preview = msg.content_preview[:80]
                    break
        if not first_match_preview:
            first_match_preview = blob_parts[0][:80] if blob_parts else ""

        scored.append((count, s, first_match_preview))

    # Sort by hit count desc, then recency desc (mirrors the Rich command).
    epoch = datetime.min.replace(tzinfo=None)
    scored.sort(key=lambda x: (x[0], x[1].start_time or epoch), reverse=True)
    scored = scored[:limit]

    rows: list[dict] = []
    for rank, (count, s, preview) in enumerate(scored, start=1):
        cost = session_cost(s)
        rows.append(
            {
                "rank": rank,
                "session_id": s.id,
                "session_id_short": short_id(s.id),
                "date": iso_or_none(s.start_time),
                "date_display": fmt_date(s.start_time),
                "agent": s.agent,
                "agent_label": agent_label(s.agent),
                "project": s.project or "",
                "match_count": int(count),
                "preview": preview,
                "preview_segments": _segment_preview(preview, query),
                "tokens": build_session_tokens(s),
                "cost_usd": cost,
                "cost_display": fmt_money(cost),
            }
        )

    empty = None
    if not rows:
        empty = build_empty_state(
            {"query": query, "agent": agent_filter, "project": project},
            "Try a broader query or remove --agent/--project filters.",
        )

    return {
        "query": query,
        "rows": rows,
        "result_count": len(rows),
        "limit": limit,
        "empty": empty,
    }
