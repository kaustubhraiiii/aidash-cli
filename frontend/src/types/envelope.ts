// Shared JSON contract primitives. Mirrors the envelope in ARCHITECTURE.md.
export type CommandName = "cost" | "replay" | "score" | "rates" | "search";
export type ErrorCode = "bad_argument" | "session_not_found" | "parse_error" | "internal";
export type Rating = "good" | "ok" | "poor";

export interface ErrorInfo {
  code: ErrorCode;
  message: string;
}

export interface Meta {
  generated_at: string; // ISO 8601
  aidash_version: string;
  period: string | null;
  filters: Record<string, string | null>;
}

export interface Envelope<T> {
  schema_version: string; // "1.0"
  command: CommandName;
  ok: boolean;
  data: T | null;
  error: ErrorInfo | null;
  meta: Meta;
}

export interface Tokens {
  input_tokens: number;
  input_tokens_display: string;
  output_tokens: number;
  output_tokens_display: string;
  cache_read_tokens: number;
  cache_read_tokens_display: string;
  cache_creation_tokens: number;
  cache_creation_tokens_display: string;
  total_tokens: number;
  total_tokens_display: string;
}

export interface DetectedAgent {
  agent: string;
  agent_label: string;
  sessions: number;
}

export interface EmptyState {
  active_filters: Record<string, string>;
  detected_agents: DetectedAgent[];
  suggestion: string;
}

export interface ExportBlock {
  format: "csv" | "json";
  content: string;
  filename_suggestion: string;
}
