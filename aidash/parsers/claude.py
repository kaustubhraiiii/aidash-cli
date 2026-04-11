"""Claude Code JSONL parser."""

import json
from datetime import datetime
from pathlib import Path

from aidash.models import Message, Session, TokenUsage, ToolCall
from aidash.parsers.base import BaseParser


class ClaudeCodeParser(BaseParser):
    def discover_sessions(self) -> list[Path]:
        """Discover Claude Code session files, skipping sub-agent files."""
        base = Path.home() / ".claude" / "projects"
        if not base.exists():
            return []
        return sorted(
            p for p in base.rglob("*.jsonl")
            if not p.name.startswith("agent-")
        )

    def parse_session(self, filepath: Path) -> Session:
        """Parse a Claude Code JSONL session file into a Session object."""
        session = Session(
            id=filepath.stem,
            agent="claude_code",
            project=self._extract_project_name(filepath),
        )

        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue

                msg_data = entry.get("message")
                if not isinstance(msg_data, dict):
                    continue

                role = msg_data.get("role")
                if role not in ("user", "assistant"):
                    continue

                # Extract timestamp
                ts = self._parse_timestamp(entry.get("timestamp"))

                # Extract content preview and tool calls
                content_preview = ""
                tool_calls: list[ToolCall] = []
                content = msg_data.get("content", [])
                if isinstance(content, str):
                    content_preview = content[:100]
                elif isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        if block.get("type") == "text" and not content_preview:
                            content_preview = block.get("text", "")[:100]
                        elif block.get("type") == "tool_use":
                            tool_calls.append(ToolCall(
                                name=block.get("name", ""),
                                timestamp=ts,
                            ))

                # Extract token usage
                usage_data = msg_data.get("usage", {})
                token_usage = TokenUsage(
                    input_tokens=usage_data.get("input_tokens", 0),
                    output_tokens=usage_data.get("output_tokens", 0),
                    cache_creation_input_tokens=usage_data.get("cache_creation_input_tokens", 0),
                    cache_read_input_tokens=usage_data.get("cache_read_input_tokens", 0),
                )

                message = Message(
                    role=role,
                    content_preview=content_preview,
                    timestamp=ts,
                    token_usage=token_usage,
                    tool_calls=tool_calls,
                )
                session.messages.append(message)

                # Aggregate token totals
                session.total_input_tokens += token_usage.input_tokens
                session.total_output_tokens += token_usage.output_tokens

                # Track session time bounds
                if ts:
                    if session.start_time is None or ts < session.start_time:
                        session.start_time = ts
                    if session.end_time is None or ts > session.end_time:
                        session.end_time = ts

                # Grab cwd and model from first entry that has them
                if not session.cwd and entry.get("cwd"):
                    session.cwd = entry["cwd"]
                    # Use cwd for accurate project name (dir heuristic is lossy)
                    session.project = Path(entry["cwd"]).name
                if not session.model and msg_data.get("model"):
                    session.model = msg_data["model"]

        return session

    @staticmethod
    def _extract_project_name(filepath: Path) -> str:
        """Derive project name from the parent directory name.

        Directory names like '-Users-xxx-projectname' encode the original path
        with leading dashes replacing slashes. Reconstruct and take the last segment.
        """
        dir_name = filepath.parent.name
        # Replace leading dashes with slashes to reconstruct the path
        reconstructed = "/" + dir_name.lstrip("-").replace("-", "/")
        return Path(reconstructed).name

    @staticmethod
    def _parse_timestamp(ts_str: str | None) -> datetime | None:
        if not ts_str:
            return None
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
