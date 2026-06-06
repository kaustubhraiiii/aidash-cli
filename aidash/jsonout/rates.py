"""JSON builder for `aidash rates`. Implemented by the RATES agent.

Returns the RatesData payload (see ARCHITECTURE.md). The CLI wraps it via
common.envelope("rates", data, ...). Do NOT touch Rich code or other modules.
"""

from __future__ import annotations

from aidash.models import Session


def build_rates_json(
    sessions: list[Session],
    *,
    period: str,
    compare: bool,
) -> dict:
    """Build the RatesData dict (models[] always; comparison when compare)."""
    raise NotImplementedError("RATES agent implements build_rates_json")
