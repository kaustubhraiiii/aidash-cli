"""Contract tests for `aidash replay --json` (ReplayData payload)."""

from __future__ import annotations

import json

from aidash.cli import cli


def _data(result):
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)  # valid JSON
    assert payload["schema_version"] == "1.0"
    assert payload["command"] == "replay"
    assert payload["ok"] is True
    return payload["data"]


def test_replay_last_json_is_valid_and_typed(runner, sample_sessions, patch_sessions):
    patch_sessions(sample_sessions)
    result = runner.invoke(cli, ["replay", "--json"])
    data = _data(result)

    assert data["target"] == "last"
    assert data["empty"] is None
    # "last" selects exactly the first session.
    assert len(data["sessions"]) == 1

    session = data["sessions"][0]
    for field in (
        "session_id",
        "session_id_short",
        "agent",
        "agent_label",
        "project",
        "model",
        "started_at",
        "started_at_display",
        "ended_at",
        "ended_at_display",
        "tokens",
        "cost_usd",
        "cost_display",
        "message_count",
        "messages",
    ):
        assert field in session, field

    assert isinstance(session["cost_usd"], float)
    assert isinstance(session["cost_display"], str)
    assert isinstance(session["message_count"], int)
    assert isinstance(session["tokens"]["input_tokens"], int)
    assert isinstance(session["tokens"]["total_tokens"], int)
    assert session["message_count"] == len(session["messages"])

    # First message: no previous, so elapsed is null and display empty.
    first = session["messages"][0]
    for field in (
        "index",
        "role",
        "content_preview",
        "timestamp",
        "timestamp_display",
        "elapsed_since_prev_seconds",
        "elapsed_display",
        "tool_calls",
        "tokens",
        "cost_usd",
        "cost_display",
    ):
        assert field in first, field

    assert isinstance(first["index"], int)
    assert first["index"] == 0
    assert first["role"] in ("user", "assistant")
    assert first["elapsed_since_prev_seconds"] is None
    assert first["elapsed_display"] == ""
    assert isinstance(first["cost_usd"], float)
    assert isinstance(first["cost_display"], str)
    assert isinstance(first["tool_calls"], list)

    # Every message: type contracts hold.
    for m in session["messages"]:
        assert isinstance(m["index"], int)
        assert isinstance(m["cost_usd"], float)
        es = m["elapsed_since_prev_seconds"]
        assert es is None or isinstance(es, int)
        if m["tokens"] is not None:
            assert isinstance(m["tokens"]["input_tokens"], int)
            assert isinstance(m["tokens"]["output_tokens"], int)
        for tc in m["tool_calls"]:
            assert isinstance(tc["name"], str)
            assert "timestamp" in tc


def test_replay_elapsed_display_format(runner, sample_sessions, patch_sessions):
    patch_sessions(sample_sessions)
    # Target the claude_code session s1 by id substring (it has 4 messages
    # with non-trivial gaps); the loader returns newest-first so "last" is s3.
    result = runner.invoke(cli, ["replay", "a1b2c3d4", "--json"])
    data = _data(result)
    assert len(data["sessions"]) == 1
    messages = data["sessions"][0]["messages"]

    # Sample session s1: msg index 2 is 9 minutes after msg index 1 (9:31 -> 9:40).
    third = messages[2]
    assert third["elapsed_since_prev_seconds"] == 9 * 60
    assert third["elapsed_display"] == "+9m00s"

    # Second message: 1 minute after the first (9:30 -> 9:31).
    second = messages[1]
    assert second["elapsed_since_prev_seconds"] == 60
    assert second["elapsed_display"] == "+1m00s"


def test_replay_today_json(runner, sample_sessions, patch_sessions):
    patch_sessions(sample_sessions)
    result = runner.invoke(cli, ["replay", "today", "--json"])
    data = _data(result)

    assert data["target"] == "today"
    # "today" selects all sessions handed to the builder.
    assert len(data["sessions"]) == len(sample_sessions)
    assert data["empty"] is None


def test_replay_empty_no_match(runner, sample_sessions, patch_sessions):
    patch_sessions(sample_sessions)
    result = runner.invoke(cli, ["replay", "zzzznomatch", "--json"])
    data = _data(result)

    assert data["target"] == "zzzznomatch"
    assert data["sessions"] == []
    assert data["empty"]["suggestion"]
    assert isinstance(data["empty"]["suggestion"], str)
