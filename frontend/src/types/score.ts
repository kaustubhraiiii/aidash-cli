import type { EmptyState, Rating } from "./envelope.js";

export interface ScoreMetric {
  key: string;
  label: string;
  raw: number;
  raw_display: string;
  score: number;
  score_display: string;
  weight: number;
  rating: Rating;
}

export interface ScoredSession {
  session_id: string;
  session_id_short: string;
  date: string;
  date_display: string;
  agent: string;
  agent_label: string;
  project: string;
  metrics: ScoreMetric[];
  total_score: number;
  total_display: string;
  verdict: string;
  rating: Rating;
}

export interface TrendWeek {
  week: string;
  avg_score: number;
  avg_display: string;
  session_count: number;
  rating: Rating;
  bar_ratio: number;
}

export interface ScoreData {
  view: "sessions" | "trend";
  target: string;
  sessions: ScoredSession[];
  weeks: TrendWeek[];
  empty: EmptyState | null;
}
