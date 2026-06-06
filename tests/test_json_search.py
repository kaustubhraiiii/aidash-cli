"""Contract tests for `aidash search --json` (build_search_json)."""

from __future__ import annotations

import json

from aidash.cli import cli


def test_search_json_is_valid_and_typed(runner, sample_sessions, patch_sessions):
    patch_sessions(sample_sessions)
    result = runner.invoke(cli, ["search", "auth", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)  # valid JSON
    assert payload["schema_version"] == "1.0"
    assert payload["command"] == "search"
    assert payload["ok"] is True

    data = payload["data"]
    assert data["query"] == "auth"
    assert data["limit"] == 10
    assert data["empty"] is None
    assert data["result_count"] >= 1
    assert data["result_count"] == len(data["rows"])

    row = data["rows"][0]
    # rank is 1-based int
    assert isinstance(row["rank"], int)
    assert row["rank"] == 1

    # ids
    assert isinstance(row["session_id"], str)
    assert isinstance(row["session_id_short"], str)
    assert len(row["session_id_short"]) == 8

    # match_count int, preview str
    assert isinstance(row["match_count"], int)
    assert row["match_count"] >= 1
    assert isinstance(row["preview"], str)

    # preview_segments is a list of {text:str, match:bool}
    assert isinstance(row["preview_segments"], list)
    for seg in row["preview_segments"]:
        assert isinstance(seg["text"], str)
        assert isinstance(seg["match"], bool)

    # money is float (never str), tokens are ints
    assert isinstance(row["cost_usd"], float)
    assert isinstance(row["cost_display"], str)
    assert isinstance(row["tokens"]["input_tokens"], int)
    assert isinstance(row["tokens"]["total_tokens"], int)

    # agent fields
    assert isinstance(row["agent"], str)
    assert isinstance(row["agent_label"], str)


def test_search_json_segments_highlight_match(runner, sample_sessions, patch_sessions):
    patch_sessions(sample_sessions)
    result = runner.invoke(cli, ["search", "auth", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)["data"]

    # At least one segment across all rows marks a matching span, and its text
    # equals the query (case-insensitively).
    matched_texts = [
        seg["text"]
        for row in data["rows"]
        for seg in row["preview_segments"]
        if seg["match"]
    ]
    assert matched_texts, "expected at least one matching preview_segment"
    assert any(t.lower() == "auth" for t in matched_texts)


def test_search_json_ranking_is_descending(runner, sample_sessions, patch_sessions):
    patch_sessions(sample_sessions)
    result = runner.invoke(cli, ["search", "auth", "--json"])

    data = json.loads(result.output)["data"]
    ranks = [row["rank"] for row in data["rows"]]
    assert ranks == list(range(1, len(ranks) + 1))

    counts = [row["match_count"] for row in data["rows"]]
    assert counts == sorted(counts, reverse=True)


def test_search_json_no_match(runner, sample_sessions, patch_sessions):
    patch_sessions(sample_sessions)
    result = runner.invoke(cli, ["search", "zzzznohitsxyz", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True

    data = payload["data"]
    assert data["rows"] == []
    assert data["result_count"] == 0
    assert data["empty"] is not None
    assert data["empty"]["suggestion"]
