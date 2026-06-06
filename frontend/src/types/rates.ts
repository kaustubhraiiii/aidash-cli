import type { EmptyState } from "./envelope.js";

export interface RateRow {
  model: string;
  session_count: number;
  input_per_million_usd: number;
  input_per_million_display: string;
  output_per_million_usd: number;
  output_per_million_display: string;
  avg_cost_per_session_usd: number;
  avg_cost_per_session_display: string;
  io_ratio_pct: number;
  io_ratio_display: string;
  cache_hit_pct: number;
  cache_hit_display: string;
  effective_rate_per_million_usd: number;
  effective_rate_per_million_display: string;
}

export interface RateEstimate {
  comparator: string;
  cost_usd: number;
  cost_display: string;
}

export interface RateComparisonRow {
  agent: string;
  agent_label: string;
  session_count: number;
  actual_cost_usd: number;
  actual_cost_display: string;
  estimates: RateEstimate[];
  cheapest: string;
}

export interface RateComparison {
  comparators: string[];
  rows: RateComparisonRow[];
}

export interface RatesData {
  period: string;
  models: RateRow[];
  comparison: RateComparison | null;
  empty: EmptyState | null;
}
