"""Tests for the raw export + weekly-Markdown output modes.

These exercise the CLI end-to-end via Click's CliRunner with the loader
patched to synthetic sessions (hermetic — see conftest.py). The export modes
print a plain string to stdout (CSV / JSON / Markdown), not a JSON envelope.
"""

from __future__ import annotations

import csv
import io
import json
import re

from aidash.cli import cli


def test_cost_export_csv(runner, sample_sessions, patch_sessions):
    patch_sessions(sample_sessions)
    result = runner.invoke(cli, ["cost", "--export", "csv"])
    assert result.exit_code == 0, result.output

    reader = csv.DictReader(io.StringIO(result.output))
    fields = reader.fieldnames
    for expected in (
        "date",
        "agent",
        "project",
        "model",
        "input_tokens",
        "output_tokens",
        "cost_usd",
    ):
        assert expected in fields

    rows = list(reader)
    assert len(rows) >= 1
    first = rows[0]
    # cost_usd must parse as a float
    float(first["cost_usd"])
    int(first["input_tokens"])


def test_cost_export_json(runner, sample_sessions, patch_sessions):
    patch_sessions(sample_sessions)
    result = runner.invoke(cli, ["cost", "--export", "json"])
    assert result.exit_code == 0, result.output

    data = json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) >= 1
    first = data[0]
    assert isinstance(first["cost_usd"], float)
    assert isinstance(first["input_tokens"], int)
    assert isinstance(first["output_tokens"], int)
    for key in ("date", "agent", "project", "model"):
        assert key in first


def test_cost_weekly_markdown(runner, sample_sessions, patch_sessions):
    patch_sessions(sample_sessions)
    result = runner.invoke(cli, ["cost", "--weekly"])
    assert result.exit_code == 0, result.output

    out = result.output
    assert "# Weekly Cost Summary" in out
    assert "|" in out  # markdown table present
    assert "| Week | Sessions | Tokens | Cost |" in out
    assert re.search(r"\d{4}-W\d{2}", out)  # at least one ISO week label
    assert "**Total:" in out


def test_score_export_csv(runner, sample_sessions, patch_sessions):
    patch_sessions(sample_sessions)
    result = runner.invoke(cli, ["score", "--export", "csv"])
    assert result.exit_code == 0, result.output

    reader = csv.DictReader(io.StringIO(result.output))
    fields = reader.fieldnames
    for expected in (
        "session_id",
        "date",
        "agent",
        "project",
        "total_score",
        "prompt_ratio_score",
        "tool_efficiency_score",
        "token_density_score",
        "session_focus_score",
    ):
        assert expected in fields

    rows = list(reader)
    assert len(rows) >= 1
    float(rows[0]["total_score"])


def test_score_export_json(runner, sample_sessions, patch_sessions):
    patch_sessions(sample_sessions)
    result = runner.invoke(cli, ["score", "--export", "json"])
    assert result.exit_code == 0, result.output

    data = json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) >= 1
    first = data[0]
    assert isinstance(first["total_score"], float)
    for metric in (
        "prompt_ratio_score",
        "tool_efficiency_score",
        "token_density_score",
        "session_focus_score",
    ):
        assert isinstance(first[metric], float)


def test_cost_export_json_empty(runner, patch_sessions):
    patch_sessions([])
    result = runner.invoke(cli, ["cost", "--export", "json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == []
