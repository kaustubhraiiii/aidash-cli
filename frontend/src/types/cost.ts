import type { Tokens, EmptyState, ExportBlock } from "./envelope.js";

export interface CostRow {
  session_id: string;
  session_id_short: string;
  date: string;
  date_display: string;
  agent: string;
  agent_label: string;
  project: string;
  model: string;
  tokens: Tokens;
  cost_usd: number;
  cost_display: string;
}

export interface CostGroupRow {
  key: string;
  key_label: string;
  session_count: number;
  tokens: Tokens;
  cost_usd: number;
  cost_display: string;
}

export interface CostTotals {
  session_count: number;
  tokens: Tokens;
  cost_usd: number;
  cost_display: string;
}

export interface CostData {
  view: "detail" | "grouped";
  period: string;
  group_by: "agent" | "project" | "model" | null;
  rows: CostRow[] | CostGroupRow[];
  totals: CostTotals;
  empty: EmptyState | null;
  export: ExportBlock | null;
  markdown: string | null;
}
