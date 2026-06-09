import { useEffect, useState, useCallback } from "react";
import { Box, Text } from "ink";
import { ScrollView } from "ink-scroll-view";
import { runReplay, EngineError } from "../engine.js";
import { Spinner, Alert, Badge } from "@/components";
import { useInput } from "@/hooks/use-input";
import type { ReplayData, ReplaySession, ReplayMessage } from "../types/index.js";

function agentVariant(agent: string): "info" | "success" | "secondary" | "default" {
  const lower = agent.toLowerCase();
  if (lower.includes("claude") || lower.includes("anthropic")) return "info";
  if (lower.includes("gemini") || lower.includes("google")) return "success";
  if (lower.includes("codex") || lower.includes("openai")) return "secondary";
  return "default";
}

function parseTarget(args: string[]): string {
  const firstNonFlag = args.find((a) => !a.startsWith("-"));
  return firstNonFlag ?? "last";
}

function extractTime(timestampDisplay: string): string {
  if (!timestampDisplay.includes(":")) return timestampDisplay;
  const parts = timestampDisplay.split(" ");
  const timePart = parts.find((p) => p.includes(":"));
  return timePart ?? timestampDisplay;
}

function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max - 1) + "…" : s;
}

function filterMessages(
  messages: ReplayMessage[],
  searchQuery: string,
): ReplayMessage[] {
  if (!searchQuery) return messages;
  const q = searchQuery.toLowerCase();
  return messages.filter(
    (m) =>
      m.content_preview.toLowerCase().includes(q) ||
      m.tool_calls.some((t) => t.name.toLowerCase().includes(q)),
  );
}

export function ReplayView({ args }: { args: string[] }) {
  const [target] = useState<string>(() => parseTarget(args));
  const [data, setData] = useState<ReplayData | null>(null);
  const [error, setError] = useState<EngineError | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [scrollOffset, setScrollOffset] = useState(0);
  const [searchMode, setSearchMode] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    runReplay({ target })
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch((e: unknown) => {
        setError(e as EngineError);
        setLoading(false);
      });
  }, [target]);

  const height = Math.max(10, (process.stdout.rows ?? 24) - 7);
  const visibleCount = height;

  const currentSession: ReplaySession | null =
    data !== null && data.sessions.length > 0
      ? (data.sessions[currentIdx] ?? null)
      : null;

  const allMessages: ReplayMessage[] = currentSession?.messages ?? [];
  const filteredMessages = filterMessages(allMessages, searchQuery);

  const maxScroll = Math.max(0, filteredMessages.length - visibleCount);

  const clampScroll = useCallback(
    (offset: number): number => Math.min(Math.max(0, offset), maxScroll),
    [maxScroll],
  );

  useInput((input, key) => {
    if (searchMode) {
      if (key.escape) {
        setSearchMode(false);
        setSearchQuery("");
        return;
      }
      if (key.backspace || key.delete) {
        setSearchQuery((q) => q.slice(0, -1));
        return;
      }
      if (input && /^[\x20-\x7E]$/.test(input)) {
        setSearchQuery((q) => q + input);
        return;
      }
      return;
    }

    if (key.escape) {
      process.exit(0);
      return;
    }
    if (input === "q") {
      process.exit(0);
      return;
    }
    if (input === "/") {
      setSearchMode(true);
      setSearchQuery("");
      setScrollOffset(0);
      return;
    }
    if (key.upArrow) {
      setScrollOffset((o) => clampScroll(o - 1));
      return;
    }
    if (key.downArrow) {
      setScrollOffset((o) => clampScroll(o + 1));
      return;
    }
    if (key.leftArrow && data !== null && data.sessions.length > 0) {
      const n = data.sessions.length;
      setCurrentIdx((i) => (i - 1 + n) % n);
      setScrollOffset(0);
      setSearchMode(false);
      setSearchQuery("");
      return;
    }
    if (key.rightArrow && data !== null && data.sessions.length > 0) {
      const n = data.sessions.length;
      setCurrentIdx((i) => (i + 1) % n);
      setScrollOffset(0);
      setSearchMode(false);
      setSearchQuery("");
      return;
    }
  });

  if (error) {
    return (
      <Box flexDirection="column" gap={1}>
        <Alert variant="error" title="aidash error">
          {error.message}
        </Alert>
        <Text dimColor>{error.suggestion}</Text>
      </Box>
    );
  }

  if (loading) {
    return <Spinner label="Loading replay…" />;
  }

  if (data === null) {
    return <Spinner label="Loading replay…" />;
  }

  if (data.empty !== null) {
    return (
      <Box flexDirection="column" gap={1}>
        <Alert variant="warning">{data.empty.suggestion}</Alert>
        {data.empty.detected_agents.map((a) => (
          <Badge key={a.agent} variant={agentVariant(a.agent)}>
            {a.agent_label}
          </Badge>
        ))}
      </Box>
    );
  }

  const sessionCount = data.sessions.length;
  const visibleMessages = filteredMessages.slice(
    scrollOffset,
    scrollOffset + visibleCount,
  );

  const headerAgent = currentSession?.agent ?? "";
  const headerAgentLabel = currentSession?.agent_label ?? "";
  const searchPrefix = searchMode ? `[Search: ${searchQuery}] ` : "";

  return (
    <Box flexDirection="column" gap={1}>
      <Box flexDirection="column">
        <Box flexDirection="row" gap={1}>
          <Text bold>
            {searchPrefix}Replay — {target}
          </Text>
          {headerAgentLabel !== "" && (
            <Badge variant={agentVariant(headerAgent)}>{headerAgentLabel}</Badge>
          )}
        </Box>
        <Box flexDirection="row" gap={2}>
          <Text dimColor>
            {sessionCount} session{sessionCount !== 1 ? "s" : ""}
          </Text>
          {sessionCount > 0 && (
            <Text dimColor>
              Session {currentIdx + 1} / {sessionCount}
            </Text>
          )}
        </Box>
      </Box>

      <ScrollView height={height}>
        <Box flexDirection="column">
          {visibleMessages.map((msg) => (
            <Box key={msg.index} flexDirection="column">
              <Box flexDirection="row" gap={1}>
                <Text dimColor>{extractTime(msg.timestamp_display)}</Text>
                {msg.role === "assistant" ? (
                  <Text bold>assistant</Text>
                ) : (
                  <Text dimColor>user</Text>
                )}
                <Text>{truncate(msg.content_preview, 100)}</Text>
                {msg.elapsed_display !== "" && (
                  <Text dimColor>(+{msg.elapsed_display})</Text>
                )}
              </Box>
              {msg.tool_calls.map((tool, ti) => (
                <Box key={ti} marginLeft={2}>
                  <Badge variant="secondary">{tool.name}</Badge>
                </Box>
              ))}
            </Box>
          ))}
        </Box>
      </ScrollView>

      <Text dimColor>{"↑↓ scroll   / search   ←→ session   q quit"}</Text>
    </Box>
  );
}
