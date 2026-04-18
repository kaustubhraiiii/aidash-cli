"""Gemini CLI JSON parser.

Gemini CLI persists chat logs under ~/.gemini/tmp/<session-id>/ as JSON files
(logs.json / chats.json / checkpoint-*.json). Messages use role "user" and
"model" (normalized to "assistant" here), and token usage is reported as
usageMetadata with promptTokenCount / candidatesTokenCount /
cachedContentTokenCount.
"""

import json
from datetime import datetime
from pathlib import Path

from aidash.models import Message, Session, TokenUsage, ToolCall
from aidash.parsers.base import BaseParser


class GeminiCliParser(BaseParser):
    def discover_sessions(self) -> list[Path]:
        """Discover Gemini CLI session files under ~/.gemini/tmp/."""
        base = Path.home() / ".gemini" / "tmp"
        if not base.exists() or not base.is_dir():
            return []
        files: list[Path] = []
        for pattern in ("logs.json", "chats.json", "checkpoint-*.json"):
            files.extend(base.rglob(pattern))
        # De-dupe and sort for determinism
        return sorted(set(files))

    def parse_session(self, filepath: Path) -> Session:
        """Parse a Gemini CLI JSON session file into a Session object."""
        session = Session(
            id=self._session_id(filepath),
            agent="gemini_cli",
            project=filepath.parent.name,
        )

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, ValueError, OSError):
            return session

        entries = self._extract_entries(data)

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            raw_role = entry.get("role", "")
            role = "assistant" if raw_role == "model" else raw_role
            if role not in ("user", "assistant"):
                continue

            ts = self._parse_timestamp(
                entry.get("timestamp")
                or entry.get("time")
                or entry.get("createdAt")
            )

            content_preview = ""
            tool_calls: list[ToolCall] = []
            parts = entry.get("parts") or entry.get("content") or []
            if isinstance(parts, str):
                content_preview = parts[:100]
            elif isinstance(parts, list):
                for block in parts:
                    if isinstance(block, str):
                        if not content_preview:
                            content_preview = block[:100]
                        continue
                    if not isinstance(block, dict):
                        continue
                    if "text" in block and not content_preview:
                        text = block.get("text", "")
                        if isinstance(text, str):
                            content_preview = text[:100]
                    fc = block.get("functionCall")
                    if isinstance(fc, dict) and fc.get("name"):
                        tool_calls.append(ToolCall(name=fc["name"], timestamp=ts))
                    tu = block.get("toolUse") or block.get("tool_use")
                    if isinstance(tu, dict) and tu.get("name"):
                        tool_calls.append(ToolCall(name=tu["name"], timestamp=ts))

            usage = entry.get("usageMetadata") or entry.get("usage") or {}
            if not isinstance(usage, dict):
                usage = {}
            token_usage = TokenUsage(
                input_tokens=int(
                    usage.get("promptTokenCount", usage.get("input_tokens", 0)) or 0
                ),
                output_tokens=int(
                    usage.get("candidatesTokenCount", usage.get("output_tokens", 0)) or 0
                ),
                cache_read_input_tokens=int(
                    usage.get(
                        "cachedContentTokenCount",
                        usage.get("cache_read_input_tokens", 0),
                    ) or 0
                ),
                cache_creation_input_tokens=int(
                    usage.get("cache_creation_input_tokens", 0) or 0
                ),
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

            if not session.model and entry.get("model"):
                session.model = entry["model"]
            if not session.cwd and entry.get("cwd"):
                session.cwd = entry["cwd"]
                session.project = Path(entry["cwd"]).name

        # Fall back to a top-level model/cwd if messages didn't carry one
        if isinstance(data, dict):
            if not session.model and isinstance(data.get("model"), str):
                session.model = data["model"]
            if not session.cwd and isinstance(data.get("cwd"), str):
                session.cwd = data["cwd"]
                session.project = Path(data["cwd"]).name

        return session

    @staticmethod
    def _extract_entries(data) -> list:
        """Pull a flat list of message entries out of the various Gemini shapes."""
        if isinstance(data, list):
            return data
        if not isinstance(data, dict):
            return []
        for key in ("messages", "history", "entries", "logs", "chat", "turns"):
            val = data.get(key)
            if isinstance(val, list):
                return val
        return []

    @staticmethod
    def _session_id(filepath: Path) -> str:
        parent = filepath.parent.name
        if parent and parent != "tmp":
            return parent
        return filepath.stem

    @staticmethod
    def _parse_timestamp(ts_str) -> datetime | None:
        if not ts_str:
            return None
        if isinstance(ts_str, (int, float)):
            try:
                # Heuristic: ms vs seconds
                if ts_str > 1e12:
                    return datetime.fromtimestamp(ts_str / 1000)
                return datetime.fromtimestamp(ts_str)
            except (ValueError, OSError, OverflowError):
                return None
        if not isinstance(ts_str, str):
            return None
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
