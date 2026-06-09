import { useEffect, useState, useCallback } from "react";
import { Box, Text } from "ink";
import { runRates, EngineError } from "../engine.js";
import { Spinner, Alert, Table, Badge } from "@/components";
import { useInput } from "@/hooks/use-input";
import type { RatesData, RateRow, RateComparisonRow } from "../types/index.js";

type Period = "today" | "weekly" | "monthly" | "all";

const PERIODS: Period[] = ["today", "weekly", "monthly", "all"];

function parsePeriod(args: string[]): Period {
  const idx = args.indexOf("--period");
  if (idx !== -1) {
    const val = args[idx + 1];
    if (val === "today" || val === "weekly" || val === "monthly" || val === "all") {
      return val;
    }
  }
  return "all";
}

function parseCompare(args: string[]): boolean {
  return args.includes("--compare");
}

type NormalTableRow = Record<string, unknown> & {
  model: string;
  sessions: string;
  input: string;
  output: string;
  effective: string;
  cache: string;
  monthly?: string;
};

type CompareTableRow = Record<string, unknown> & {
  agent: string;
  sessions: string;
  actual: string;
  cheapest: string;
};

export function RatesView({ args }: { args: string[] }) {
  const [period, setPeriod] = useState<Period>(() => parsePeriod(args));
  const [compareMode, setCompareMode] = useState<boolean>(() => parseCompare(args));
  const [data, setData] = useState<RatesData | null>(null);
  const [error, setError] = useState<EngineError | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback((p: Period, compare: boolean) => {
    setLoading(true);
    setData(null);
    setError(null);

    runRates({ period: p, compare })
      .then((result) => {
        setData(result);
        setLoading(false);
      })
      .catch((e: unknown) => {
        setError(e as EngineError);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    fetchData(period, compareMode);
  }, []);

  useInput((input) => {
    if (input === "c") {
      const newCompare = !compareMode;
      setCompareMode(newCompare);
      fetchData(period, newCompare);
      return;
    }
    if (input === "p") {
      const idx = PERIODS.indexOf(period);
      const newPeriod = PERIODS[(idx + 1) % PERIODS.length]!;
      setPeriod(newPeriod);
      fetchData(newPeriod, compareMode);
      return;
    }
    if (input === "q") {
      process.exit(0);
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
    return <Spinner label="Loading rates…" />;
  }

  if (!data) {
    return <Spinner label="Loading rates…" />;
  }

  if (data.empty) {
    return (
      <Box flexDirection="column" gap={1}>
        <Alert variant="warning">{data.empty.suggestion}</Alert>
        {data.empty.detected_agents.map((a) => (
          <Badge key={a.agent}>{a.agent_label}</Badge>
        ))}
      </Box>
    );
  }

  if (data.comparison !== null) {
    const comparison = data.comparison;
    const comparatorCols = comparison.comparators.map((c) => ({
      key: c,
      header: c,
      width: 14 as const,
      align: "right" as const,
    }));

    const columns = [
      { key: "agent", header: "Agent", width: 20 },
      { key: "sessions", header: "Sessions", width: 9, align: "right" as const },
      { key: "actual", header: "Actual", width: 12, align: "right" as const },
      ...comparatorCols,
      { key: "cheapest", header: "Cheapest", width: 22 },
    ];

    const tableData: CompareTableRow[] = comparison.rows.map((r: RateComparisonRow) => {
      const row: CompareTableRow = {
        agent: r.agent_label,
        sessions: String(r.session_count),
        actual: r.actual_cost_display,
        cheapest: r.cheapest,
      };
      for (const est of r.estimates) {
        row[est.comparator] = est.cost_display;
      }
      return row;
    });

    return (
      <Box flexDirection="column" gap={1}>
        <Text bold>{"Rates — compare — " + data.period}</Text>
        <Table<CompareTableRow>
          data={tableData}
          columns={columns}
          maxRows={25}
        />
        <Text dimColor>c=toggle compare   p=cycle period   q quit</Text>
      </Box>
    );
  }

  const isMonthly = period === "monthly";

  const baseColumns = [
    { key: "model", header: "Model", width: 30 },
    { key: "sessions", header: "Sessions", width: 9, align: "right" as const },
    { key: "input", header: "In$/1M", width: 12, align: "right" as const },
    { key: "output", header: "Out$/1M", width: 12, align: "right" as const },
    { key: "effective", header: "Eff$/1M", width: 12, align: "right" as const },
    { key: "cache", header: "Cache%", width: 8, align: "right" as const },
  ];

  const columns = isMonthly
    ? [...baseColumns, { key: "monthly", header: "Est/month", width: 12, align: "right" as const }]
    : baseColumns;

  const tableData: NormalTableRow[] = data.models.map((r: RateRow) => {
    const row: NormalTableRow = {
      model: r.model.length > 28 ? r.model.slice(0, 26) + "…" : r.model,
      sessions: String(r.session_count),
      input: r.input_per_million_display,
      output: r.output_per_million_display,
      effective: r.effective_rate_per_million_display,
      cache: r.cache_hit_display,
    };
    if (isMonthly) {
      row["monthly"] = "$" + (r.avg_cost_per_session_usd * r.session_count).toFixed(2);
    }
    return row;
  });

  return (
    <Box flexDirection="column" gap={1}>
      <Text bold>{"Rates — " + data.period}</Text>
      <Table<NormalTableRow>
        data={tableData}
        columns={columns}
        maxRows={25}
      />
      <Text dimColor>c=toggle compare   p=cycle period   q quit</Text>
    </Box>
  );
}
