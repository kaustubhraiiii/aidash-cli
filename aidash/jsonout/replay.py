"""JSON builder for `aidash replay`. Implemented by the REPLAY agent.

Returns the ReplayData payload (see ARCHITECTURE.md). The CLI wraps it via
common.envelope("replay", data, ...). Do NOT touch Rich code or other modules.
"""

from __future__ import annotations

from aidash.jsonout.common import (
    agent_label,
    build_empty_state,
    build_session_tokens,
    build_tokens,
    fmt_datetime,
    fmt_money,
    iso_or_none,
    message_cost,
    pricing_for_agent,
    session_cost,
    short_id,
)
from aidash.models import Message, Session


def _elapsed_display(secs: int | None) -> str:
    """Format elapsed seconds the same way as _render_session in cli.py."""
    if not secs or secs <= 0:
        return ""
    if secs >= 60:
        return f"+{secs // 60}m{secs % 60:02d}s"
    return f"+{secs}s"


def _build_message(msg: Message, index: int, pricing, prev_time) -> dict:
    # Elapsed since the previous message in the same session.
    elapsed_seconds: int | None = None
    if msg.timestamp and prev_time:
        delta = int((msg.timestamp - prev_time).total_seconds())
        elapsed_seconds = delta

    usage = msg.token_usage
    if usage:
        tokens = build_tokens(
            usage.input_tokens,
            usage.output_tokens,
            usage.cache_read_input_tokens,
            usage.cache_creation_input_tokens,
        )
        cost = message_cost(usage.input_tokens, usage.output_tokens, pricing)
    else:
        tokens = None
        cost = 0.0

    return {
        "index": index,
        "role": msg.role,
        "content_preview": msg.content_preview,
        "timestamp": iso_or_none(msg.timestamp),
        "timestamp_display": fmt_datetime(msg.timestamp),
        "elapsed_since_prev_seconds": elapsed_seconds,
        "elapsed_display": _elapsed_display(elapsed_seconds),
        "tool_calls": [
            {"name": tc.name, "timestamp": iso_or_none(tc.timestamp)}
            for tc in msg.tool_calls
        ],
        "tokens": tokens,
        "cost_usd": cost,
        "cost_display": fmt_money(cost),
    }


def _build_session(session: Session) -> dict:
    pricing = pricing_for_agent(session.agent)

    messages: list[dict] = []
    prev_time = None
    for index, msg in enumerate(session.messages):
        messages.append(_build_message(msg, index, pricing, prev_time))
        prev_time = msg.timestamp

    cost = session_cost(session)
    return {
        "session_id": session.id,
        "session_id_short": short_id(session.id),
        "agent": session.agent,
        "agent_label": agent_label(session.agent),
        "project": session.project,
        "model": session.model,
        "started_at": iso_or_none(session.start_time),
        "started_at_display": fmt_datetime(session.start_time),
        "ended_at": iso_or_none(session.end_time),
        "ended_at_display": fmt_datetime(session.end_time),
        "tokens": build_session_tokens(session),
        "cost_usd": cost,
        "cost_display": fmt_money(cost),
        "message_count": len(session.messages),
        "messages": messages,
    }


def build_replay_json(sessions: list[Session], *, target: str) -> dict:
    """Build the ReplayData dict for target = last | today | <id substring>.

    `sessions` is already period-scoped by the CLI (today is pre-filtered);
    select within it: last -> first session, today -> all, else id substring.
    """
    if target == "last":
        selected = sessions[:1]
    elif target == "today":
        selected = list(sessions)
    else:
        selected = [s for s in sessions if target in s.id]

    if not selected:
        empty = build_empty_state(
            {"target": target},
            "Check the session id (try 'aidash search' to find one).",
        )
        return {"target": target, "sessions": [], "empty": empty}

    return {
        "target": target,
        "sessions": [_build_session(s) for s in selected],
        "empty": None,
    }
