"""Shared pytest fixtures for the --json / export contract tests.

These fixtures are HERMETIC: they never read ~/.claude or any real logs. Tests
invoke commands through Click's CliRunner and patch
``aidash.cli.load_all_sessions`` so the engine sees synthetic Session objects.

Typical usage in a per-command test file::

    import json
    from aidash.cli import cli

    def test_cost_json(runner, sample_sessions, patch_sessions):
        patch_sessions(sample_sessions)
        result = runner.invoke(cli, ["cost", "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["ok"] is True
"""

from __future__ import annotations

from datetime import datetime

import pytest
from click.testing import CliRunner

from aidash.models import Message, Session, TokenUsage, ToolCall


def _msg(role, text, *, inp=0, out=0, cr=0, cc=0, tools=(), ts=None):
    return Message(
        role=role,
        content_preview=text,
        timestamp=ts,
        token_usage=TokenUsage(
            input_tokens=inp,
            output_tokens=out,
            cache_creation_input_tokens=cc,
            cache_read_input_tokens=cr,
        )
        if (inp or out or cr or cc)
        else None,
        tool_calls=[ToolCall(name=n, timestamp=ts) for n in tools],
    )


def _make_sample_sessions() -> list[Session]:
    """Three sessions across three agents, two ISO weeks, with cache + tools."""
    # Week A
    s1 = Session(
        id="a1b2c3d4-1111-2222-3333-444455556666",
        agent="claude_code",
        project="alpha",
        model="claude-sonnet-4-5",
        start_time=datetime(2026, 5, 18, 9, 30),
        end_time=datetime(2026, 5, 18, 10, 15),
        cwd="/home/dev/alpha",
        total_input_tokens=1_500_000,
        total_output_tokens=42_000,
        messages=[
            _msg("user", "fix the auth bug in login", ts=datetime(2026, 5, 18, 9, 30)),
            _msg(
                "assistant",
                "Looking at the auth flow",
                inp=1_500_000,
                out=20_000,
                cr=800_000,
                cc=120_000,
                tools=["Read", "Grep"],
                ts=datetime(2026, 5, 18, 9, 31),
            ),
            _msg("user", "now add a test", ts=datetime(2026, 5, 18, 9, 40)),
            _msg(
                "assistant",
                "Adding a pytest case",
                out=22_000,
                tools=["Edit", "Bash"],
                ts=datetime(2026, 5, 18, 9, 41),
            ),
        ],
    )
    # Week A, different agent (no cache pricing)
    s2 = Session(
        id="b2c3d4e5-2222-3333-4444-555566667777",
        agent="codex",
        project="beta",
        model="gpt-5.4",
        start_time=datetime(2026, 5, 19, 14, 0),
        end_time=datetime(2026, 5, 19, 14, 20),
        cwd="/home/dev/beta",
        total_input_tokens=300_000,
        total_output_tokens=15_000,
        messages=[
            _msg("user", "refactor the auth module", ts=datetime(2026, 5, 19, 14, 0)),
            _msg(
                "assistant",
                "Refactoring now",
                inp=300_000,
                out=15_000,
                tools=["Read", "Edit"],
                ts=datetime(2026, 5, 19, 14, 2),
            ),
        ],
    )
    # Week B, gemini with cache reads
    s3 = Session(
        id="c3d4e5f6-3333-4444-5555-666677778888",
        agent="gemini_cli",
        project="alpha",
        model="gemini-2.5-pro",
        start_time=datetime(2026, 5, 26, 11, 0),
        end_time=datetime(2026, 5, 26, 11, 30),
        cwd="/home/dev/alpha",
        total_input_tokens=900_000,
        total_output_tokens=30_000,
        messages=[
            _msg("user", "document the search feature", ts=datetime(2026, 5, 26, 11, 0)),
            _msg(
                "assistant",
                "Writing docs",
                inp=900_000,
                out=30_000,
                cr=400_000,
                tools=["Read", "Write"],
                ts=datetime(2026, 5, 26, 11, 5),
            ),
        ],
    )
    return [s3, s2, s1]  # loader returns newest-first


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def sample_sessions() -> list[Session]:
    return _make_sample_sessions()


@pytest.fixture
def patch_sessions(monkeypatch):
    """Return a patcher: call patch_sessions(sessions) to make every
    load_all_sessions() call in the CLI return that list (any args)."""

    def _patch(sessions: list[Session]) -> list[Session]:
        monkeypatch.setattr(
            "aidash.cli.load_all_sessions", lambda *a, **k: list(sessions)
        )
        return sessions

    return _patch
