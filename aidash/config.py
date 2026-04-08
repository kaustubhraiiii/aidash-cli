"""Agent detection and path constants."""

from pathlib import Path

AGENT_PATHS: dict[str, list[Path]] = {
    "claude_code": [Path.home() / ".claude" / "projects"],
    "codex": [
        Path.home() / ".codex" / "sessions",
        Path.home() / ".codex" / "history.jsonl",
    ],
}


def detect_agents() -> list[str]:
    """Detect which AI coding agents are installed on this machine."""
    detected = []
    for agent, paths in AGENT_PATHS.items():
        for p in paths:
            if p.exists():
                detected.append(agent)
                break
    return detected
