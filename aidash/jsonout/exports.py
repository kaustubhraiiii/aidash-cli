"""Export + weekly-Markdown builders. Implemented by the EXPORT agent.

These power the raw (non-envelope) output modes:
  * `aidash cost --export csv|json`   -> build_cost_export(...)  -> str to stdout
  * `aidash score --export csv|json`  -> build_score_export(...) -> str to stdout
  * `aidash cost --weekly`            -> build_weekly_markdown(...) -> str to stdout

Each returns a plain string (CSV / JSON / Markdown). Do NOT touch Rich code or
other modules.
"""

from __future__ import annotations

import csv
import io
import json

from aidash.jsonout.common import agent_label, fmt_date, fmt_money, session_cost
from aidash.models import Session
from aidash.scoring import score_session


def build_cost_export(
    sessions: list[Session],
    *,
    fmt: str,
    period: str,
    group_by: str | None,
) -> str:
    """Return cost data serialized as CSV (fmt="csv") or JSON (fmt="json").

    One flat record per session with keys:
        date, agent, project, model, input_tokens, output_tokens, cost_usd
    Cost stays numeric (float) in both formats; tokens are ints.
    """
    rows = []
    for s in sessions:
        rows.append(
            {
                "date": fmt_date(s.start_time),
                "agent": s.agent,
                "project": s.project,
                "model": s.model,
                "input_tokens": int(s.total_input_tokens),
                "output_tokens": int(s.total_output_tokens),
                "cost_usd": round(session_cost(s), 6),
            }
        )

    if fmt == "json":
        return json.dumps(rows)

    # CSV
    fields = [
        "date",
        "agent",
        "project",
        "model",
        "input_tokens",
        "output_tokens",
        "cost_usd",
    ]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(fields)
    for row in rows:
        writer.writerow([row[f] for f in fields])
    return buf.getvalue()


def build_score_export(
    sessions: list[Session],
    *,
    fmt: str,
    target: str,
    trend: bool,
) -> str:
    """Return score data serialized as CSV (fmt="csv") or JSON (fmt="json").

    One record per session with keys:
        session_id, date, agent, project, total_score,
        prompt_ratio_score, tool_efficiency_score,
        token_density_score, session_focus_score

    Judgment call: ``target`` and ``trend`` are accepted for signature
    compatibility but ignored — the export always serializes every provided
    session scored, since an export is most useful as a complete dump.
    """
    rows = []
    for s in sessions:
        result = score_session(s)
        rows.append(
            {
                "session_id": s.id,
                "date": fmt_date(s.start_time),
                "agent": s.agent,
                "project": s.project,
                "total_score": float(result.total),
                "prompt_ratio_score": float(result.prompt_ratio_score),
                "tool_efficiency_score": float(result.tool_efficiency_score),
                "token_density_score": float(result.token_density_score),
                "session_focus_score": float(result.session_focus_score),
            }
        )

    if fmt == "json":
        return json.dumps(rows)

    fields = [
        "session_id",
        "date",
        "agent",
        "project",
        "total_score",
        "prompt_ratio_score",
        "tool_efficiency_score",
        "token_density_score",
        "session_focus_score",
    ]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(fields)
    for row in rows:
        writer.writerow([row[f] for f in fields])
    return buf.getvalue()


def build_weekly_markdown(sessions: list[Session], *, period: str) -> str:
    """Return a Markdown weekly cost summary.

    Groups sessions by ISO week ("YYYY-Www"), summing tokens (input + output)
    and cost. Sessions with no ``start_time`` are bucketed under "unknown".
    """
    # week label -> {sessions, tokens, cost}
    buckets: dict[str, dict] = {}
    for s in sessions:
        if s.start_time is not None:
            iso_year, iso_week, _ = s.start_time.isocalendar()
            label = f"{iso_year}-W{iso_week:02d}"
        else:
            label = "unknown"
        bucket = buckets.setdefault(
            label, {"sessions": 0, "tokens": 0, "cost": 0.0}
        )
        bucket["sessions"] += 1
        bucket["tokens"] += int(s.total_input_tokens) + int(s.total_output_tokens)
        bucket["cost"] += session_cost(s)

    # Sort: known weeks chronologically, "unknown" last.
    def sort_key(item):
        label = item[0]
        return (1, "") if label == "unknown" else (0, label)

    ordered = sorted(buckets.items(), key=sort_key)

    lines = ["# Weekly Cost Summary", ""]
    lines.append("| Week | Sessions | Tokens | Cost |")
    lines.append("| --- | --- | --- | --- |")

    total_sessions = 0
    total_tokens = 0
    total_cost = 0.0
    for label, b in ordered:
        total_sessions += b["sessions"]
        total_tokens += b["tokens"]
        total_cost += b["cost"]
        lines.append(
            f"| {label} | {b['sessions']} | {b['tokens']} | {fmt_money(b['cost'])} |"
        )

    lines.append("")
    lines.append(
        f"**Total: {total_sessions} sessions, {total_tokens} tokens, "
        f"{fmt_money(total_cost)}**"
    )

    return "\n".join(lines) + "\n"
