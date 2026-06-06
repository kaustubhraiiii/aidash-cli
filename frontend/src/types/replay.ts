import type { Tokens, EmptyState } from "./envelope.js";

export interface ToolCallInfo {
  name: string;
  timestamp: string | null;
}

export interface ReplayMessage {
  index: number;
  role: "user" | "assistant";
  content_preview: string;
  timestamp: string | null;
  timestamp_display: string;
  elapsed_since_prev_seconds: number | null;
  elapsed_display: string;
  tool_calls: ToolCallInfo[];
  tokens: Tokens | null;
  cost_usd: number;
  cost_display: string;
}

export interface ReplaySession {
  session_id: string;
  session_id_short: string;
  agent: string;
  agent_label: string;
  project: string;
  model: string;
  started_at: string | null;
  started_at_display: string;
  ended_at: string | null;
  ended_at_display: string;
  tokens: Tokens;
  cost_usd: number;
  cost_display: string;
  message_count: number;
  messages: ReplayMessage[];
}

export interface ReplayData {
  target: string;
  sessions: ReplaySession[];
  empty: EmptyState | null;
}
