"""Agent detection, path constants, and pricing."""

from dataclasses import dataclass
from pathlib import Path

AGENT_PATHS: dict[str, list[Path]] = {
    "claude_code": [Path.home() / ".claude" / "projects"],
    "codex": [
        Path.home() / ".codex" / "sessions",
        Path.home() / ".codex" / "history.jsonl",
    ],
    "gemini_cli": [Path.home() / ".gemini" / "tmp"],
}


@dataclass(frozen=True)
class Pricing:
    input_per_million: float
    output_per_million: float
    cache_read_per_million: float = 0.0
    cache_write_per_million: float = 0.0


# Per-agent pricing (USD per 1M tokens) — keyed by agent name
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
    "gemini_cli": Pricing(
        input_per_million=1.25,
        output_per_million=10.00,
        cache_read_per_million=0.315,
    ),
}

# Per-model pricing (USD per 1M tokens) — keyed by model name
PER_MODEL_PRICING: dict[str, Pricing] = {
    "claude-sonnet-4-5": Pricing(
        input_per_million=3.00,
        output_per_million=15.00,
        cache_read_per_million=0.30,
        cache_write_per_million=3.75,
    ),
    "claude-opus-4-6": Pricing(
        input_per_million=15.00,
        output_per_million=75.00,
        cache_read_per_million=1.50,
        cache_write_per_million=18.75,
    ),
    "claude-haiku-4-5": Pricing(
        input_per_million=0.80,
        output_per_million=4.00,
        cache_read_per_million=0.08,
        cache_write_per_million=1.00,
    ),
    "gpt-5.4": Pricing(
        input_per_million=2.50,
        output_per_million=10.00,
    ),
    "gpt-5.4-mini": Pricing(
        input_per_million=0.40,
        output_per_million=1.60,
    ),
    "gemini-2.5-pro": Pricing(
        input_per_million=1.25,
        output_per_million=10.00,
        cache_read_per_million=0.315,
    ),
    "gemini-2.5-flash": Pricing(
        input_per_million=0.15,
        output_per_million=0.60,
        cache_read_per_million=0.0375,
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
