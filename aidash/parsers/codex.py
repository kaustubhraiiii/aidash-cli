"""OpenAI Codex parser."""

import json
from datetime import datetime
from pathlib import Path

from aidash.models import Message, Session, TokenUsage, ToolCall
from aidash.parsers.base import BaseParser


class CodexParser(BaseParser):
    def discover_sessions(self) -> list[Path]:
        """Discover Codex session files.

        Checks ~/.codex/sessions/ first; falls back to ~/.codex/history.jsonl.
        """
        sessions_dir = Path.home() / ".codex" / "sessions"
        if sessions_dir.is_dir():
            files = sorted(sessions_dir.rglob("*.jsonl"))
            if files:
                return files

        history_file = Path.home() / ".codex" / "history.jsonl"
        if history_file.is_file():
            return [history_file]

        return []

    def parse_session(self, filepath: Path) -> Session:
        """Parse a Codex JSONL session file into a Session object."""
        session = Session(
            id=filepath.stem,
            agent="codex",
            project=self._extract_project(filepath),
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

                # Normalize: Codex may have role at top level or nested under "message"
                msg_data = entry.get("message")
                if isinstance(msg_data, dict):
                    role = msg_data.get("role", entry.get("role", ""))
                else:
                    role = entry.get("role", "")
                    msg_data = entry  # treat the whole entry as the message

                if role not in ("user", "assistant"):
                    continue

                ts = self._parse_timestamp(
                    entry.get("timestamp") or entry.get("created_at")
                )

                # Extract content preview and tool calls
                content_preview = ""
                tool_calls: list[ToolCall] = []
                content = msg_data.get("content", "")
                if isinstance(content, str):
                    content_preview = content[:100]
                elif isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        btype = block.get("type", "")
                        if btype == "text" and not content_preview:
                            content_preview = block.get("text", "")[:100]
                        elif btype in ("tool_use", "function_call"):
                            tool_calls.append(ToolCall(
                                name=block.get("name", block.get("function", "")),
                                timestamp=ts,
                            ))

                # Normalize token usage: try message.usage, then top-level usage
                usage_data = {}
                if isinstance(msg_data, dict):
                    usage_data = msg_data.get("usage", {})
                if not usage_data:
                    usage_data = entry.get("usage", {})

                token_usage = TokenUsage(
                    input_tokens=usage_data.get("input_tokens",
                                  usage_data.get("prompt_tokens", 0)),
                    output_tokens=usage_data.get("output_tokens",
                                   usage_data.get("completion_tokens", 0)),
                    cache_creation_input_tokens=usage_data.get(
                        "cache_creation_input_tokens", 0),
                    cache_read_input_tokens=usage_data.get(
                        "cache_read_input_tokens", 0),
                )

                message = Message(
                    role=role,
                    content_preview=content_preview,
                    timestamp=ts,
                    token_usage=token_usage,
                    tool_calls=tool_calls,
                )
                session.messages.append(message)

                session.total_input_tokens += token_usage.input_tokens
                session.total_output_tokens += token_usage.output_tokens

                if ts:
                    if session.start_time is None or ts < session.start_time:
                        session.start_time = ts
                    if session.end_time is None or ts > session.end_time:
                        session.end_time = ts

                if not session.cwd:
                    cwd = entry.get("cwd") or (
                        msg_data.get("cwd") if isinstance(msg_data, dict) else None
                    )
                    if cwd:
                        session.cwd = cwd
                        session.project = Path(cwd).name

                if not session.model:
                    model = entry.get("model") or (
                        msg_data.get("model") if isinstance(msg_data, dict) else None
                    )
                    if model:
                        session.model = model

        return session

    @staticmethod
    def _extract_project(filepath: Path) -> str:
        """Derive project name from filepath context."""
        # For history.jsonl there's no project directory structure
        if filepath.name == "history.jsonl":
            return ""
        # For session dirs, use parent directory name
        return filepath.parent.name

    @staticmethod
    def _parse_timestamp(ts_str: str | None) -> datetime | None:
        if not ts_str:
            return None
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
