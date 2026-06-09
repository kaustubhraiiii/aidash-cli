"""Contract tests for `aidash cost --json` (build_cost_json)."""

from __future__ import annotations

import json

from aidash.cli import cli


def test_cost_json_detail_valid_and_typed(runner, sample_sessions, patch_sessions):
    patch_sessions(sample_sessions)
    result = runner.invoke(cli, ["cost", "--json"])
    assert result.exit_code == 0

    payload = json.loads(result.output)  # parses as JSON
    assert payload["schema_version"] == "1.0"
    assert payload["ok"] is True
    assert payload["command"] == "cost"

    data = payload["data"]
    # required fields on data
    for field in (
        "view",
        "period",
        "group_by",
        "rows",
        "totals",
        "empty",
        "export",
        "markdown",
    ):
        assert field in data
    assert data["view"] == "detail"
    assert data["group_by"] is None
    assert data["empty"] is None
    assert data["export"] is None
    assert data["markdown"] is None

    # required fields on a detail row
    row = data["rows"][0]
    for field in (
        "session_id",
        "session_id_short",
        "date",
        "date_display",
        "agent",
        "agent_label",
        "project",
        "model",
        "tokens",
        "cost_usd",
        "cost_display",
    ):
        assert field in row

    # TYPES
    assert isinstance(row["cost_usd"], float)
    assert not isinstance(row["cost_usd"], str)
    assert isinstance(row["cost_display"], str)
    assert isinstance(row["session_id_short"], str)
    assert len(row["session_id_short"]) <= 8
    assert isinstance(row["tokens"]["input_tokens"], int)

    # totals
    totals = data["totals"]
    for field in ("session_count", "tokens", "cost_usd", "cost_display"):
        assert field in totals
    assert isinstance(totals["session_count"], int)
    assert totals["session_count"] == len(sample_sessions)
    assert isinstance(totals["cost_usd"], float)
    assert isinstance(totals["cost_display"], str)
    assert isinstance(totals["tokens"]["input_tokens"], int)


def test_cost_json_grouped(runner, sample_sessions, patch_sessions):
    patch_sessions(sample_sessions)
    result = runner.invoke(cli, ["cost", "--by", "agent", "--json"])
    assert result.exit_code == 0

    data = json.loads(result.output)["data"]
    assert data["view"] == "grouped"
    assert data["group_by"] == "agent"

    rows = data["rows"]
    assert rows, "grouped rows should not be empty"
    for row in rows:
        for field in (
            "key",
            "key_label",
            "session_count",
            "tokens",
            "cost_usd",
            "cost_display",
        ):
            assert field in row
        assert isinstance(row["key"], str)
        assert isinstance(row["key_label"], str)
        assert isinstance(row["session_count"], int)
        assert isinstance(row["cost_usd"], float)
        assert isinstance(row["cost_display"], str)

    # sorted by cost_usd descending
    costs = [r["cost_usd"] for r in rows]
    assert costs == sorted(costs, reverse=True)


def test_cost_json_empty(runner, patch_sessions):
    patch_sessions([])
    result = runner.invoke(cli, ["cost", "--json"])
    assert result.exit_code == 0

    payload = json.loads(result.output)
    assert payload["ok"] is True
    data = payload["data"]
    assert data["rows"] == []
    assert data["totals"]["session_count"] == 0
    assert data["totals"]["cost_usd"] == 0
    assert data["totals"]["tokens"]["input_tokens"] == 0
    assert data["empty"] is not None
    suggestion = data["empty"]["suggestion"]
    assert isinstance(suggestion, str) and suggestion
