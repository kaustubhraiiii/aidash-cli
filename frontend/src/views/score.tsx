import { useEffect, useState, useCallback } from "react";
import { Box, Text } from "ink";
import { runScore, EngineError } from "../engine.js";
import { Spinner, Alert, Table, BarChart, Badge } from "@/components";
import { useInput } from "@/hooks/use-input";
import type { ScoreData, ScoredSession } from "../types/index.js";
import type { Rating } from "../types/index.js";

function parseArgs(args: string[]): { target: string; trendMode: boolean } {
  let target = "last";
  let trendMode = false;
  for (const arg of args) {
    if (arg === "--trend") {
      trendMode = true;
    } else if (!arg.startsWith("--")) {
      target = arg;
    }
  }
  return { target, trendMode };
}

function scoreColor(total: number): string {
  if (total < 50) return "red";
  if (total < 75) return "yellow";
  return "green";
}

function ratingVariant(rating: Rating): "success" | "warning" | "error" {
  if (rating === "good") return "success";
  if (rating === "ok") return "warning";
  return "error";
}

type MetricRow = Record<string, unknown> & {
  metric: string;
  weight: string;
  raw: string;
  score: string;
  rating: string;
};

type TrendRow = Record<string, unknown> & {
  week: string;
  sessions: string;
  avg: string;
  rating: string;
};

function SessionPanel({ session }: { session: ScoredSession }) {
  const color = scoreColor(session.total_score);

  const metricRows: MetricRow[] = session.metrics.map((m) => ({
    metric: m.label,
    weight: (m.weight * 100).toFixed(0) + "%",
    raw: m.raw_display,
    score: m.score_display,
    rating: m.rating,
  }));

  return (
    <Box flexDirection="column" gap={1}>
      <Box justifyContent="center">
        <Text bold color={color}>
          {session.total_display}
        </Text>
      </Box>
      <Box flexDirection="row" gap={2}>
        <Text>{session.verdict}</Text>
        <Badge variant={ratingVariant(session.rating)}>{session.rating}</Badge>
      </Box>
      <Box flexDirection="row" gap={2}>
        <Badge>{session.agent_label}</Badge>
        <Text dimColor>
          {session.date_display}{"  "}{session.project}
        </Text>
      </Box>
      <Table<MetricRow>
        data={metricRows}
        columns={[
          { key: "metric", header: "Metric", width: 22 },
          { key: "weight", header: "Weight", width: 8, align: "right" },
          { key: "raw", header: "Raw", width: 12, align: "right" },
          { key: "score", header: "Score", width: 10, align: "right" },
          { key: "rating", header: "Rating", width: 8 },
        ]}
      />
    </Box>
  );
}

export function ScoreView({ args }: { args: string[] }) {
  const initial = parseArgs(args);
  const [target] = useState<string>(initial.target);
  const [trendMode, setTrendMode] = useState<boolean>(initial.trendMode);
  const [data, setData] = useState<ScoreData | null>(null);
  const [error, setError] = useState<EngineError | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentIdx, setCurrentIdx] = useState(0);

  const fetchData = useCallback(
    (t: string, trend: boolean) => {
      setLoading(true);
      setData(null);
      setError(null);
      setCurrentIdx(0);
      runScore({ target: t, trend })
        .then((result) => {
          setData(result);
          setLoading(false);
        })
        .catch((e: unknown) => {
          setError(e as EngineError);
          setLoading(false);
        });
    },
    []
  );

  useEffect(() => {
    fetchData(target, trendMode);
  }, []);

  useInput((input, key) => {
    if (input === "t") {
      const next = !trendMode;
      setTrendMode(next);
      fetchData(target, next);
      return;
    }
    if (input === "q") {
      process.exit(0);
    }
    if (data !== null && data.view === "sessions" && data.sessions.length > 1) {
      if (key.upArrow) {
        setCurrentIdx((prev) => (prev > 0 ? prev - 1 : prev));
        return;
      }
      if (key.downArrow) {
        setCurrentIdx((prev) =>
          prev < data.sessions.length - 1 ? prev + 1 : prev
        );
        return;
      }
    }
    void key;
  });

  if (error !== null) {
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
    return <Spinner label="Loading score…" />;
  }

  if (data === null) {
    return <Spinner label="Loading score…" />;
  }

  if (data.empty !== null) {
    return (
      <Box flexDirection="column" gap={1}>
        <Alert variant="warning">{data.empty.suggestion}</Alert>
        {data.empty.detected_agents.map((a) => (
          <Badge key={a.agent}>{a.agent_label}</Badge>
        ))}
        <Text dimColor>t=trend   ↑↓ navigate   q quit</Text>
      </Box>
    );
  }

  if (data.view === "trend") {
    const chartData = data.weeks.map((w) => ({
      label: w.week,
      value: Math.round(w.avg_score),
    }));

    const trendRows: TrendRow[] = data.weeks.map((w) => ({
      week: w.week,
      sessions: String(w.session_count),
      avg: w.avg_display,
      rating: w.rating,
    }));

    return (
      <Box flexDirection="column" gap={1}>
        <BarChart
          data={chartData}
          direction="horizontal"
          width={55}
          showValues={true}
          title="Score trend (last 8 weeks)"
        />
        <Table<TrendRow>
          data={trendRows}
          columns={[
            { key: "week", header: "Week", width: 12 },
            { key: "sessions", header: "Sessions", width: 9, align: "right" },
            { key: "avg", header: "Avg", width: 8, align: "right" },
            { key: "rating", header: "Rating", width: 8 },
          ]}
        />
        <Text dimColor>t=trend   ↑↓ navigate   q quit</Text>
      </Box>
    );
  }

  const sessions = data.sessions;
  const session = sessions[currentIdx];

  if (session === undefined) {
    return (
      <Box flexDirection="column" gap={1}>
        <Alert variant="warning">No sessions found.</Alert>
        <Text dimColor>t=trend   ↑↓ navigate   q quit</Text>
      </Box>
    );
  }

  return (
    <Box flexDirection="column" gap={1}>
      {sessions.length > 1 && (
        <Text bold>
          Session {currentIdx + 1} / {sessions.length}
        </Text>
      )}
      <SessionPanel session={session} />
      <Text dimColor>t=trend   ↑↓ navigate   q quit</Text>
    </Box>
  );
}
