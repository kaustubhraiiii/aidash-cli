"""Export + weekly-Markdown builders. Implemented by the EXPORT agent.

These power the raw (non-envelope) output modes:
  * `aidash cost --export csv|json`   -> build_cost_export(...)  -> str to stdout
  * `aidash score --export csv|json`  -> build_score_export(...) -> str to stdout
  * `aidash cost --weekly`            -> build_weekly_markdown(...) -> str to stdout

Each returns a plain string (CSV / JSON / Markdown). Do NOT touch Rich code or
other modules.
"""

from __future__ import annotations

from aidash.models import Session


def build_cost_export(
    sessions: list[Session],
    *,
    fmt: str,
    period: str,
    group_by: str | None,
) -> str:
    """Return cost data serialized as CSV (fmt="csv") or JSON (fmt="json")."""
    raise NotImplementedError("EXPORT agent implements build_cost_export")


def build_score_export(
    sessions: list[Session],
    *,
    fmt: str,
    target: str,
    trend: bool,
) -> str:
    """Return score data serialized as CSV (fmt="csv") or JSON (fmt="json")."""
    raise NotImplementedError("EXPORT agent implements build_score_export")


def build_weekly_markdown(sessions: list[Session], *, period: str) -> str:
    """Return a Markdown weekly cost summary."""
    raise NotImplementedError("EXPORT agent implements build_weekly_markdown")
