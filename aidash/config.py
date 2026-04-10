"""Agent detection, path constants, and pricing."""

from dataclasses import dataclass
from pathlib import Path

AGENT_PATHS: dict[str, list[Path]] = {
    "claude_code": [Path.home() / ".claude" / "projects"],
    "codex": [
        Path.home() / ".codex" / "sessions",
        Path.home() / ".codex" / "history.jsonl",
    ],
}


@dataclass(frozen=True)
class Pricing:
    input_per_million: float
    output_per_million: float
    cache_read_per_million: float = 0.0
    cache_write_per_million: float = 0.0


# Per-agent pricing (USD per 1M tokens)
MODEL_PRICING: dict[str, Pricing] = {
    "claude_code": Pricing(
        input_per_million=3.00,
        output_per_million=15.00,
        cache_read_per_million=0.30,
        cache_write_per_million=3.75,
    ),
    "codex": Pricing(
        input_per_million=2.50,
        output_per_million=10.00,
    ),
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
