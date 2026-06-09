"""JSON builder for `aidash score`. Implemented by the SCORE agent.

Returns the ScoreData payload (see ARCHITECTURE.md). The CLI wraps it via
common.envelope("score", data, ...). Do NOT touch Rich code or other modules.
"""

from __future__ import annotations

from datetime import date

from aidash.jsonout.common import (
    agent_label,
    build_empty_state,
    fmt_date,
    iso_or_none,
    rating,
    short_id,
)
from aidash.models import Session
from aidash.scoring import ScoreResult, score_session


def _verdict(total: float) -> str:
    """Mirror cli._verdict thresholds."""
    if total >= 70:
        return "Efficient session"
    if total >= 40:
        return "Room for improvement"
    return "Rough session — lots of back and forth"


def _build_metrics(result: ScoreResult) -> list[dict]:
    """Build the four ScoreMetric dicts, mirroring cli._render_score formatting."""
    specs = [
        (
            "prompt_ratio",
            "Prompt ratio",
            0.30,
            result.prompt_ratio_raw,
            f"{result.prompt_ratio_raw:.2f}",
            result.prompt_ratio_score,
        ),
        (
            "tool_efficiency",
            "Tool efficiency",
            0.25,
            result.tool_efficiency_raw,
            f"{result.tool_efficiency_raw:.2f}",
            result.tool_efficiency_score,
        ),
        (
            "token_density",
            "Token density",
            0.25,
            result.token_density_raw,
            f"{result.token_density_raw:.0f}",
            result.token_density_score,
        ),
        (
            "session_focus",
            "Session focus",
            0.20,
            result.session_focus_raw,
            f"{result.session_focus_raw} tools",
            result.session_focus_score,
        ),
    ]
    metrics = []
    for key, label, weight, raw, raw_display, score in specs:
        metrics.append(
            {
                "key": key,
                "label": label,
                "raw": raw,
                "raw_display": raw_display,
                "score": score,
                "score_display": f"{score:.0f}",
                "weight": weight,
                "rating": rating(score),
            }
        )
    return metrics


def _build_scored_session(session: Session) -> dict:
    result = score_session(session)
    total = result.total
    return {
        "session_id": session.id,
        "session_id_short": short_id(session.id),
        "date": iso_or_none(session.start_time),
        "date_display": fmt_date(session.start_time),
        "agent": session.agent,
        "agent_label": agent_label(session.agent),
        "project": session.project,
        "metrics": _build_metrics(result),
        "total_score": total,
        "total_display": f"{total:.0f}/100",
        "verdict": _verdict(total),
        "rating": rating(total),
    }


def _build_trend(sessions: list[Session], target: str) -> dict:
    weeks: dict[str, list[float]] = {}
    for s in sessions:
        if not s.start_time:
            continue
        iso = s.start_time.isocalendar()
        week_label = f"{iso[0]}-W{iso[1]:02d}"
        result = score_session(s)
        weeks.setdefault(week_label, []).append(result.total)

    sorted_weeks = sorted(weeks.keys())[-8:]

    if not sorted_weeks:
        return {
            "view": "trend",
            "target": target,
            "sessions": [],
            "weeks": [],
            "empty": build_empty_state(
                {"target": target, "trend": True},
                "Sessions exist but none have parseable timestamps for trending.",
            ),
        }

    week_rows = []
    for week in sorted_weeks:
        scores = weeks[week]
        avg = sum(scores) / len(scores)
        week_rows.append(
            {
                "week": week,
                "avg_score": avg,
                "avg_display": f"{avg:.0f}",
                "session_count": len(scores),
                "rating": rating(avg),
                "bar_ratio": avg / 100.0,
            }
        )

    return {
        "view": "trend",
        "target": target,
        "sessions": [],
        "weeks": week_rows,
        "empty": None,
    }


def _select_sessions(sessions: list[Session], target: str) -> list[Session]:
    """Mirror the Rich score command's target selection."""
    if target == "last":
        return sessions[:1]
    if target == "today":
        today = date.today()
        return [s for s in sessions if s.start_time and s.start_time.date() == today]
    if target == "all":
        return list(sessions)
    return [s for s in sessions if target in s.id]


def build_score_json(
    sessions: list[Session],
    *,
    target: str,
    trend: bool,
) -> dict:
    """Build the ScoreData dict (view "sessions" or, when trend, "trend")."""
    if trend:
        return _build_trend(sessions, target)

    selected = _select_sessions(sessions, target)

    if not selected:
        return {
            "view": "sessions",
            "target": target,
            "sessions": [],
            "weeks": [],
            "empty": build_empty_state(
                {"target": target, "trend": False},
                "No sessions matched. Try a different target (e.g. 'all').",
            ),
        }

    return {
        "view": "sessions",
        "target": target,
        "sessions": [_build_scored_session(s) for s in selected],
        "weeks": [],
        "empty": None,
    }
