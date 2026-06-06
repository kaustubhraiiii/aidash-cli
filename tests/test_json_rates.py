"""Contract tests for `aidash rates --json`."""

from __future__ import annotations

import json

from aidash.cli import cli


def test_rates_json_is_valid_and_typed(runner, sample_sessions, patch_sessions):
    patch_sessions(sample_sessions)
    result = runner.invoke(cli, ["rates", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)  # valid JSON
    assert payload["schema_version"] == "1.0"
    assert payload["command"] == "rates"
    assert payload["ok"] is True

    data = payload["data"]
    assert data["comparison"] is None
    assert data["empty"] is None
    assert isinstance(data["models"], list) and data["models"]

    row = data["models"][0]
    assert isinstance(row["session_count"], int)
    assert isinstance(row["input_per_million_usd"], float)
    assert isinstance(row["input_per_million_display"], str)
    assert isinstance(row["output_per_million_usd"], float)
    assert isinstance(row["avg_cost_per_session_usd"], float)
    assert isinstance(row["avg_cost_per_session_display"], str)
    assert isinstance(row["io_ratio_pct"], float)
    assert isinstance(row["io_ratio_display"], str)
    assert isinstance(row["cache_hit_pct"], float)
    assert isinstance(row["cache_hit_display"], str)
    assert isinstance(row["effective_rate_per_million_usd"], float)
    assert isinstance(row["effective_rate_per_million_display"], str)

    # Models are sorted by model name.
    models = [m["model"] for m in data["models"]]
    assert models == sorted(models)


def test_rates_compare_json(runner, sample_sessions, patch_sessions):
    patch_sessions(sample_sessions)
    result = runner.invoke(cli, ["rates", "--compare", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True

    comparison = payload["data"]["comparison"]
    assert comparison is not None
    assert isinstance(comparison["comparators"], list) and comparison["comparators"]
    assert all(isinstance(c, str) for c in comparison["comparators"])

    assert isinstance(comparison["rows"], list) and comparison["rows"]
    crow = comparison["rows"][0]
    assert isinstance(crow["agent"], str)
    assert isinstance(crow["agent_label"], str)
    assert isinstance(crow["session_count"], int)
    assert isinstance(crow["actual_cost_usd"], float)
    assert isinstance(crow["actual_cost_display"], str)
    assert isinstance(crow["estimates"], list) and crow["estimates"]
    assert isinstance(crow["cheapest"], str)
    assert crow["cheapest"] in comparison["comparators"]

    est = crow["estimates"][0]
    assert est["comparator"] in comparison["comparators"]
    assert isinstance(est["cost_usd"], float)
    assert isinstance(est["cost_display"], str)


def test_rates_json_empty(runner, patch_sessions):
    patch_sessions([])
    result = runner.invoke(cli, ["rates", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)["data"]
    assert data["models"] == []
    assert data["comparison"] is None
    assert data["empty"]["suggestion"]
