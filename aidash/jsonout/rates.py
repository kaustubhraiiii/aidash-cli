"""JSON builder for `aidash rates`. Implemented by the RATES agent.

Returns the RatesData payload (see ARCHITECTURE.md). The CLI wraps it via
common.envelope("rates", data, ...). Do NOT touch Rich code or other modules.
"""

from __future__ import annotations

from aidash.config import MODEL_PRICING
from aidash.models import Session

from .common import (
    agent_label,
    build_empty_state,
    fmt_money,
    fmt_pct,
    resolve_model_pricing,
    session_cost,
)


def _build_models(sessions: list[Session]) -> list[dict]:
    """Per-model rate rows, mirroring `_rates_table` in cli.py."""
    groups: dict[str, list[Session]] = {}
    for s in sessions:
        model = s.model or "unknown"
        groups.setdefault(model, []).append(s)

    rows: list[dict] = []
    for model, model_sessions in sorted(groups.items()):
        pricing = resolve_model_pricing(model, model_sessions)

        total_cost = 0.0
        total_input = 0
        total_output = 0
        total_cache_read = 0
        total_cache_write = 0

        for s in model_sessions:
            total_cost += session_cost(s)
            for msg in s.messages:
                u = msg.token_usage
                if not u:
                    continue
                total_input += u.input_tokens
                total_output += u.output_tokens
                total_cache_read += u.cache_read_input_tokens
                total_cache_write += u.cache_creation_input_tokens

        n = len(model_sessions)
        avg_cost = total_cost / n if n else 0.0

        io_total = total_input + total_output
        io_ratio = (total_input / io_total * 100) if io_total > 0 else 0.0

        input_side = total_input + total_cache_read + total_cache_write
        cache_hit = (total_cache_read / input_side * 100) if input_side > 0 else 0.0

        all_tokens = input_side + total_output
        effective = (total_cost / all_tokens * 1_000_000) if all_tokens > 0 else 0.0

        rows.append(
            {
                "model": model,
                "session_count": n,
                "input_per_million_usd": pricing.input_per_million,
                "input_per_million_display": fmt_money(pricing.input_per_million, 2),
                "output_per_million_usd": pricing.output_per_million,
                "output_per_million_display": fmt_money(pricing.output_per_million, 2),
                "avg_cost_per_session_usd": avg_cost,
                "avg_cost_per_session_display": fmt_money(avg_cost, 4),
                "io_ratio_pct": io_ratio,
                "io_ratio_display": fmt_pct(io_ratio, 0),
                "cache_hit_pct": cache_hit,
                "cache_hit_display": fmt_pct(cache_hit, 1),
                "effective_rate_per_million_usd": effective,
                "effective_rate_per_million_display": fmt_money(effective, 2),
            }
        )
    return rows


def _build_comparison(sessions: list[Session]) -> dict:
    """What-if cost comparison, mirroring `_rates_compare` in cli.py."""
    agent_groups: dict[str, dict] = {}
    for s in sessions:
        agent = s.agent
        if agent not in agent_groups:
            agent_groups[agent] = {
                "sessions": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read": 0,
                "cache_write": 0,
                "actual_cost": 0.0,
            }
        g = agent_groups[agent]
        g["sessions"] += 1
        g["actual_cost"] += session_cost(s)
        for msg in s.messages:
            u = msg.token_usage
            if not u:
                continue
            g["input_tokens"] += u.input_tokens
            g["output_tokens"] += u.output_tokens
            g["cache_read"] += u.cache_read_input_tokens
            g["cache_write"] += u.cache_creation_input_tokens

    comparators = [
        (label, MODEL_PRICING[key])
        for label, key in (
            ("Claude", "claude_code"),
            ("Gemini", "gemini_cli"),
            ("Codex", "codex"),
        )
        if key in MODEL_PRICING
    ]

    rows: list[dict] = []
    for agent, g in sorted(agent_groups.items()):
        inp = g["input_tokens"]
        out = g["output_tokens"]
        cr = g["cache_read"]
        cw = g["cache_write"]

        estimates: list[dict] = []
        cheapest_label: str | None = None
        cheapest_cost: float | None = None
        for label, pricing in comparators:
            cost = (
                inp * pricing.input_per_million / 1_000_000
                + out * pricing.output_per_million / 1_000_000
                + cr * pricing.cache_read_per_million / 1_000_000
                + cw * pricing.cache_write_per_million / 1_000_000
            )
            # Agents without caching charge cache tokens at input rate
            if pricing.cache_read_per_million == 0.0:
                cost = (
                    (inp + cr + cw) * pricing.input_per_million / 1_000_000
                    + out * pricing.output_per_million / 1_000_000
                )
            estimates.append(
                {
                    "comparator": label,
                    "cost_usd": cost,
                    "cost_display": fmt_money(cost, 4),
                }
            )
            if cheapest_cost is None or cost < cheapest_cost:
                cheapest_cost = cost
                cheapest_label = label

        rows.append(
            {
                "agent": agent,
                "agent_label": agent_label(agent),
                "session_count": g["sessions"],
                "actual_cost_usd": g["actual_cost"],
                "actual_cost_display": fmt_money(g["actual_cost"], 4),
                "estimates": estimates,
                "cheapest": cheapest_label,
            }
        )

    return {
        "comparators": [label for label, _ in comparators],
        "rows": rows,
    }


def build_rates_json(
    sessions: list[Session],
    *,
    period: str,
    compare: bool,
) -> dict:
    """Build the RatesData dict (models[] always; comparison when compare)."""
    if not sessions:
        return {
            "period": period,
            "models": [],
            "comparison": None,
            "empty": build_empty_state(
                {"period": period},
                "Try removing filters or expanding --period.",
            ),
        }

    return {
        "period": period,
        "models": _build_models(sessions),
        "comparison": _build_comparison(sessions) if compare else None,
        "empty": None,
    }
