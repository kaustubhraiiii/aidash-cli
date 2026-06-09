import type { Tokens, EmptyState } from "./envelope.js";

export interface PreviewSegment {
  text: string;
  match: boolean;
}

export interface SearchRow {
  rank: number;
  session_id: string;
  session_id_short: string;
  date: string;
  date_display: string;
  agent: string;
  agent_label: string;
  project: string;
  match_count: number;
  preview: string;
  preview_segments: PreviewSegment[];
  tokens: Tokens;
  cost_usd: number;
  cost_display: string;
}

export interface SearchData {
  query: string;
  rows: SearchRow[];
  result_count: number;
  limit: number;
  empty: EmptyState | null;
}
