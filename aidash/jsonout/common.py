"""Shared helpers for the --json output contract.

Every command's JSON builder lives in its own module (cost.py, replay.py, ...)
and assembles its `data` payload from the helpers here. The CLI wraps that
payload in the standard envelope via `envelope()`.

Naming rules (enforced by these helpers, mirrored in ARCHITECTURE.md):
  * money      -> <x>_usd (float) + <x>_display (str, "$0.1234")
  * tokens     -> <x>_tokens (int) + <x>_tokens_display (str, "1.5M")
  * percent    -> <x>_pct (float 0-100) + <x>_display (str, "60%")
  * timestamp  -> <x>_at (ISO str | None) + <x>_at_display (str)
  * rating     -> "good" (>=70) / "ok" (>=40) / "poor"
  * agent      -> agent (key) + agent_label (human)
"""

from __future__ import annotations

from datetime import datetime, timezone

from aidash.config import MODEL_PRICING, PER_MODEL_PRICING, Pricing
from aidash.models import Session

SCHEMA_VERSION = "1.0"
AIDASH_VERSION = "0.2.0"

AGENT_LABELS: dict[str, str] = {
    "claude_code": "Claude Code",
    "gemini_cli": "Gemini CLI",
    "codex": "Codex",
}


# --------------------------------------------------------------------------- #
# Scalar formatters
# --------------------------------------------------------------------------- #
def fmt_tokens(n: int) -> str:
    """Abbreviate a token count: 1500000 -> "1.5M", 12000 -> "12.0K"."""
    n = int(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def fmt_money(value: float, decimals: int = 4) -> str:
    """Format a dollar amount: 0.1234 -> "$0.1234" (costs) or "$3.00" (rates)."""
    return f"${value:.{decimals}f}"


def fmt_pct(value: float, decimals: int = 0) -> str:
    """Format a percentage: 60.0 -> "60%"."""
    return f"{value:.{decimals}f}%"


def iso_or_none(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def fmt_datetime(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else "—"


def fmt_date(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%d") if dt else "—"


def short_id(session_id: str) -> str:
    return (session_id or "")[:8]


def agent_label(agent: str) -> str:
    return AGENT_LABELS.get(agent, agent or "—")


def rating(value: float) -> str:
    """Map a 0-100 value to a rating bucket (matches the Rich colour gates)."""
    if value >= 70:
        return "good"
    if value >= 40:
        return "ok"
    return "poor"


# --------------------------------------------------------------------------- #
# Tokens blocks
# --------------------------------------------------------------------------- #
def build_tokens(inp: int, out: int, cache_read: int, cache_creation: int) -> dict:
    """Build the canonical Tokens object (5 raw fields + 5 display strings)."""
    total = inp + out + cache_read + cache_creation
    return {
        "input_tokens": inp,
        "input_tokens_display": fmt_tokens(inp),
        "output_tokens": out,
        "output_tokens_display": fmt_tokens(out),
        "cache_read_tokens": cache_read,
        "cache_read_tokens_display": fmt_tokens(cache_read),
        "cache_creation_tokens": cache_creation,
        "cache_creation_tokens_display": fmt_tokens(cache_creation),
        "total_tokens": total,
        "total_tokens_display": fmt_tokens(total),
    }


def _session_cache_totals(session: Session) -> tuple[int, int]:
    cache_read = cache_creation = 0
    for msg in session.messages:
        u = msg.token_usage
        if not u:
            continue
        cache_read += u.cache_read_input_tokens
        cache_creation += u.cache_creation_input_tokens
    return cache_read, cache_creation


def build_session_tokens(session: Session) -> dict:
    """Tokens block for a single session.

    input/output come from the session totals (matching the Rich tables);
    cache figures are summed from messages.
    """
    cache_read, cache_creation = _session_cache_totals(session)
    return build_tokens(
        session.total_input_tokens,
        session.total_output_tokens,
        cache_read,
        cache_creation,
    )


def build_tokens_for_sessions(sessions: list[Session]) -> dict:
    """Aggregate Tokens block across many sessions (totals / group rows)."""
    inp = out = cache_read = cache_creation = 0
    for s in sessions:
        inp += s.total_input_tokens
        out += s.total_output_tokens
        cr, cc = _session_cache_totals(s)
        cache_read += cr
        cache_creation += cc
    return build_tokens(inp, out, cache_read, cache_creation)


# --------------------------------------------------------------------------- #
# Pricing / cost (mirrors aidash.cli, kept here so builders stay independent)
# --------------------------------------------------------------------------- #
def pricing_for_agent(agent: str) -> Pricing:
    return MODEL_PRICING.get(agent, MODEL_PRICING["claude_code"])


def resolve_model_pricing(model: str, sessions: list[Session]) -> Pricing:
    if model in PER_MODEL_PRICING:
        return PER_MODEL_PRICING[model]
    if sessions:
        return MODEL_PRICING.get(sessions[0].agent, MODEL_PRICING["claude_code"])
    return MODEL_PRICING["claude_code"]


def session_cost(session: Session) -> float:
    """Dollar cost for a session based on its agent's pricing."""
    pricing = pricing_for_agent(session.agent)
    cost = 0.0
    for msg in session.messages:
        u = msg.token_usage
        if not u:
            continue
        cost += u.input_tokens * pricing.input_per_million / 1_000_000
        cost += u.output_tokens * pricing.output_per_million / 1_000_000
        cost += u.cache_read_input_tokens * pricing.cache_read_per_million / 1_000_000
        cost += (
            u.cache_creation_input_tokens * pricing.cache_write_per_million / 1_000_000
        )
    return cost


def message_cost(input_tokens: int, output_tokens: int, pricing: Pricing) -> float:
    return (
        input_tokens * pricing.input_per_million / 1_000_000
        + output_tokens * pricing.output_per_million / 1_000_000
    )


# --------------------------------------------------------------------------- #
# Empty state + envelope
# --------------------------------------------------------------------------- #
def detected_agents_list() -> list[dict]:
    """Best-effort detected-agent summary for empty states. Never raises."""
    out: list[dict] = []
    try:
        from aidash.config import detect_agents
        from aidash.loader import PARSER_MAP

        for agent in detect_agents():
            try:
                count = len(PARSER_MAP[agent]().discover_sessions())
            except Exception:
                count = 0
            out.append(
                {"agent": agent, "agent_label": agent_label(agent), "sessions": count}
            )
    except Exception:
        pass
    return out


def build_empty_state(active_filters: dict | None, suggestion: str) -> dict:
    """The data.empty object emitted when a command matches no sessions."""
    cleaned = {
        k: str(v)
        for k, v in (active_filters or {}).items()
        if v not in (None, "", "all")
    }
    return {
        "active_filters": cleaned,
        "detected_agents": detected_agents_list(),
        "suggestion": suggestion,
    }


def envelope(
    command: str,
    data: dict | None,
    *,
    period: str | None = None,
    filters: dict | None = None,
    ok: bool = True,
    error: dict | None = None,
) -> dict:
    """Wrap a command's data payload in the standard contract envelope."""
    norm_filters: dict[str, str | None] = {}
    for k, v in (filters or {}).items():
        norm_filters[k] = None if v is None else str(v)
    return {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "ok": ok,
        "data": data,
        "error": error,
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "aidash_version": AIDASH_VERSION,
            "period": period,
            "filters": norm_filters,
        },
    }
