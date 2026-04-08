"""Dataclasses for Session, Message, TokenUsage, and ToolCall."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass
class ToolCall:
    name: str = ""
    timestamp: datetime | None = None


@dataclass
class Message:
    role: str = ""  # "user" or "assistant"
    content_preview: str = ""  # first 100 chars
    timestamp: datetime | None = None
    token_usage: TokenUsage | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass
class Session:
    id: str = ""
    agent: str = ""
    project: str = ""
    start_time: datetime | None = None
    end_time: datetime | None = None
    messages: list[Message] = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    model: str = ""
    cwd: str = ""
