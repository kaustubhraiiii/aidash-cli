"""JSON / export output layer for aidash.

The CLI imports the builders from here; each builder lives in its own module so
they can be developed independently. `common` holds shared helpers and the
envelope.
"""

from aidash.jsonout.common import envelope
from aidash.jsonout.cost import build_cost_json
from aidash.jsonout.exports import (
    build_cost_export,
    build_score_export,
    build_weekly_markdown,
)
from aidash.jsonout.rates import build_rates_json
from aidash.jsonout.replay import build_replay_json
from aidash.jsonout.score import build_score_json
from aidash.jsonout.search import build_search_json

__all__ = [
    "envelope",
    "build_cost_json",
    "build_replay_json",
    "build_score_json",
    "build_rates_json",
    "build_search_json",
    "build_cost_export",
    "build_score_export",
    "build_weekly_markdown",
]
