"""Contract tests for the `score` --json builder (aidash.jsonout.score)."""

from __future__ import annotations

import json

from aidash.cli import cli

RATINGS = {"good", "ok", "poor"}


def test_score_json_sessions_view(runner, sample_sessions, patch_sessions):
    patch_sessions(sample_sessions)
    result = runner.invoke(cli, ["score", "--json"])
    assert result.exit_code == 0

    payload = json.loads(result.output)  # valid JSON
    assert payload["schema_version"] == "1.0"
    assert payload["command"] == "score"
    assert payload["ok"] is True

    data = payload["data"]
    assert data["view"] == "sessions"
    assert data["weeks"] == []
    assert data["empty"] is None
    assert len(data["sessions"]) >= 1

    session = data["sessions"][0]
    metrics = session["metrics"]
    assert isinstance(metrics, list)
    assert len(metrics) == 4

    keys = {m["key"] for m in metrics}
    assert keys == {
        "prompt_ratio",
        "tool_efficiency",
        "token_density",
        "session_focus",
    }

    for m in metrics:
        assert isinstance(m["score"], (int, float))
        assert m["rating"] in RATINGS
        assert isinstance(m["score_display"], str)
        assert isinstance(m["weight"], float)
        assert isinstance(m["raw_display"], str)

    assert isinstance(session["total_score"], (int, float))
    assert isinstance(session["total_display"], str)
    assert session["rating"] in RATINGS
    assert isinstance(session["verdict"], str)


def test_score_json_all_target(runner, sample_sessions, patch_sessions):
    patch_sessions(sample_sessions)
    result = runner.invoke(cli, ["score", "all", "--json"])
    assert result.exit_code == 0

    data = json.loads(result.output)["data"]
    assert data["view"] == "sessions"
    assert len(data["sessions"]) == len(sample_sessions)


def test_score_json_trend_view(runner, sample_sessions, patch_sessions):
    patch_sessions(sample_sessions)
    result = runner.invoke(cli, ["score", "--trend", "--json"])
    assert result.exit_code == 0

    payload = json.loads(result.output)
    assert payload["ok"] is True

    data = payload["data"]
    assert data["view"] == "trend"
    assert data["sessions"] == []
    assert data["empty"] is None
    assert len(data["weeks"]) >= 1

    week = data["weeks"][0]
    assert isinstance(week["week"], str)
    assert isinstance(week["session_count"], int)
    assert 0.0 <= week["bar_ratio"] <= 1.0
    assert week["rating"] in RATINGS
    assert isinstance(week["avg_score"], (int, float))
    assert isinstance(week["avg_display"], str)


def test_score_json_empty(runner, patch_sessions):
    patch_sessions([])
    result = runner.invoke(cli, ["score", "--json"])
    assert result.exit_code == 0

    data = json.loads(result.output)["data"]
    assert data["sessions"] == []
    assert data["empty"]["suggestion"]
