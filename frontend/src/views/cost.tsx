import { useEffect, useState, useCallback } from "react";
import { Box, Text } from "ink";
import { runEngine, EngineError } from "../engine.js";
import { Spinner, Alert, Table, BarChart, Badge } from "@/components";
import { useInput } from "@/hooks/use-input";
import type { CostData, CostRow, CostGroupRow } from "../types/index.js";

type Period = "today" | "weekly" | "monthly" | "all";
type GroupBy = "agent" | "project" | "model" | null;

const PERIODS: Period[] = ["today", "weekly", "monthly", "all"];
const PERIOD_KEYS: Record<string, Period> = {
  "1": "today",
  "2": "weekly",
  "3": "monthly",
  "4": "all",
};

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

function parseGroupBy(args: string[]): GroupBy {
  const idx = args.indexOf("--by");
  if (idx !== -1) {
    const val = args[idx + 1];
    if (val === "agent" || val === "project" || val === "model") {
      return val;
    }
  }
  return null;
}

function buildArgs(period: Period, groupBy: GroupBy): string[] {
  const out: string[] = ["--period", period];
  if (groupBy) {
    out.push("--by", groupBy);
  }
  return out;
}

function isCostRow(row: CostRow | CostGroupRow): row is CostRow {
  return "date" in row;
}

/** Bucket the last 7 calendar days from detail rows. Returns buckets sorted oldest→newest. */
function buildSparkline(
  rows: (CostRow | CostGroupRow)[]
): { label: string; value: number }[] {
  const detailRows = rows.filter(isCostRow);

  const today = new Date();
  const buckets: Map<string, number> = new Map();

  // Build the 7-day window
  for (let i = 6; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const label = `${d.getMonth() + 1}/${d.getDate()}`;
    buckets.set(label, 0);
  }

  for (const row of detailRows) {
    // date_display e.g. "Jan 5" or "2025-01-05" — try to normalise
    const raw = row.date ?? "";
    // Parse from ISO date string if available
    let d: Date | null = null;
    if (/^\d{4}-\d{2}-\d{2}/.test(raw)) {
      d = new Date(raw + "T00:00:00");
    } else {
      // Attempt a rough parse of date_display (e.g. "Jan 5")
      d = new Date(row.date_display + " " + today.getFullYear());
    }
    if (!d || isNaN(d.getTime())) continue;

    const key = `${d.getMonth() + 1}/${d.getDate()}`;
    if (buckets.has(key)) {
      buckets.set(key, (buckets.get(key) ?? 0) + row.cost_usd);
    }
  }

  return Array.from(buckets.entries()).map(([label, value]) => ({
    label,
    value: Math.round(value * 10000) / 10000, // round to 4dp to avoid NaN from float drift
  }));
}

/** Format cost in USD as a short string for sparkline labels. */
function fmtUsd(v: number): string {
  if (v === 0) return "$0";
  if (v < 0.01) return "<$0.01";
  return `$${v.toFixed(2)}`;
}

/** Badge variant for a given agent key. */
function agentVariant(agent: string): "info" | "success" | "secondary" | "default" {
  const lower = agent.toLowerCase();
  if (lower.includes("claude") || lower.includes("anthropic")) return "info";
  if (lower.includes("gemini") || lower.includes("google")) return "success";
  if (lower.includes("codex") || lower.includes("openai")) return "secondary";
  return "default";
}

type TableRowDetail = Record<string, unknown> & {
  date: string;
  agent: string;
  project: string;
  model: string;
  cost: string;
  tokens: string;
};

type TableRowGrouped = Record<string, unknown> & {
  group: string;
  sessions: string;
  tokens: string;
  cost: string;
};

export function CostView({ args }: { args: string[] }) {
  const [period, setPeriod] = useState<Period>(() => parsePeriod(args));
  const [groupBy, setGroupBy] = useState<GroupBy>(() => parseGroupBy(args));
  const [data, setData] = useState<CostData | null>(null);
  const [detailData, setDetailData] = useState<CostData | null>(null);
  const [error, setError] = useState<EngineError | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [exportResult, setExportResult] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  const fetchData = useCallback(
    (p: Period, g: GroupBy) => {
      setLoading(true);
      setData(null);
      setError(null);
      setExportResult(null);
      setExportError(null);

      const fetchArgs = buildArgs(p, g);

      // When grouped, also fetch detail data for sparkline
      if (g) {
        const detailArgs = buildArgs(p, null);
        Promise.all([
          runEngine<CostData>("cost", fetchArgs),
          runEngine<CostData>("cost", detailArgs),
        ])
          .then(([groupedEnv, detailEnv]) => {
            setData(groupedEnv.data);
            setDetailData(detailEnv.data);
            setLoading(false);
          })
          .catch((e: unknown) => {
            setError(e as EngineError);
            setLoading(false);
          });
      } else {
        runEngine<CostData>("cost", fetchArgs)
          .then((env) => {
            setData(env.data);
            setDetailData(env.data); // same data for sparkline in detail mode
            setLoading(false);
          })
          .catch((e: unknown) => {
            setError(e as EngineError);
            setLoading(false);
          });
      }
    },
    []
  );

  useEffect(() => {
    fetchData(period, groupBy);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleExport = useCallback(
    (format: "csv" | "json") => {
      if (exporting) return;
      setExporting(true);
      setExportResult(null);
      setExportError(null);

      const exportArgs = [...buildArgs(period, groupBy), "--export", format];
      // Spawn via runEngine won't work for export (mutually exclusive with --json).
      // Use the engine directly without --json flag by spawning the process ourselves.
      import("node:child_process").then(({ spawn }) => {
        const PYTHON_BIN = process.env["AIDASH_PYTHON"] ?? "python3";
        const argv = ["-m", "aidash", "cost", ...buildArgs(period, groupBy), "--export", format];
        let stdout = "";
        let stderr = "";
        let child;
        try {
          child = spawn(PYTHON_BIN, argv, { stdio: ["ignore", "pipe", "pipe"] });
        } catch (e) {
          setExportError(`Could not start Python: ${String(e)}`);
          setExporting(false);
          return;
        }
        child.stdout.on("data", (c: Buffer) => { stdout += c.toString(); });
        child.stderr.on("data", (c: Buffer) => { stderr += c.toString(); });
        child.on("close", (code: number | null) => {
          setExporting(false);
          if (code !== 0) {
            setExportError(
              `Export failed (exit ${code ?? "?"})` + (stderr ? `: ${stderr.trim()}` : "")
            );
            return;
          }
          // The engine writes the file and prints the path (or raw content).
          // Show the first line of stdout as the "path" if it looks like one.
          const firstLine = stdout.trim().split("\n")[0] ?? "";
          const pathLike = firstLine.length > 0 && !firstLine.startsWith("{") && !firstLine.startsWith("date");
          setExportResult(
            pathLike
              ? `Exported to: ${firstLine}`
              : `Export complete (${format.toUpperCase()}, ${stdout.length} bytes)`
          );
        });
      }).catch((e: unknown) => {
        setExportError(`Import error: ${String(e)}`);
        setExporting(false);
      });
      void exportArgs; // suppress unused warning
    },
    [period, groupBy, exporting]
  );

  useInput((input, key) => {
    // Period switching: 1-4 keys or 'p' to cycle
    if (PERIOD_KEYS[input]) {
      const newPeriod = PERIOD_KEYS[input]!;
      if (newPeriod !== period) {
        setPeriod(newPeriod);
        fetchData(newPeriod, groupBy);
      }
      return;
    }
    if (input === "p") {
      const idx = PERIODS.indexOf(period);
      const newPeriod = PERIODS[(idx + 1) % PERIODS.length]!;
      setPeriod(newPeriod);
      fetchData(newPeriod, groupBy);
      return;
    }
    // Toggle grouping
    if (input === "g") {
      const newGroupBy: GroupBy = groupBy === "agent" ? null : "agent";
      setGroupBy(newGroupBy);
      fetchData(period, newGroupBy);
      return;
    }
    // Export
    if (input === "e" || input === "E") {
      handleExport("csv");
      return;
    }
    if (input === "j" || input === "J") {
      handleExport("json");
      return;
    }
    void key; // suppress unused warning
  });

  // ── Render states ──────────────────────────────────────────────────────────

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
    return <Spinner label="Loading cost…" />;
  }

  if (!data) {
    return <Spinner label="Loading cost…" />;
  }

  if (data.empty) {
    const detected = data.empty.detected_agents;
    return (
      <Box flexDirection="column" gap={1}>
        <Alert variant="warning" title="No sessions matched">
          {data.empty.suggestion}
        </Alert>
        {detected.length > 0 && (
          <Box flexDirection="column">
            <Text bold>Detected agents:</Text>
            {detected.map((a) => (
              <Box key={a.agent} flexDirection="row" gap={1}>
                <Badge variant={agentVariant(a.agent)}>{a.agent_label}</Badge>
                <Text dimColor>{a.sessions} session{a.sessions !== 1 ? "s" : ""}</Text>
              </Box>
            ))}
          </Box>
        )}
      </Box>
    );
  }

  // Build sparkline from detail data (guards against grouped-only rows lacking dates)
  const sparklineSource = detailData ?? data;
  const sparklineItems = buildSparkline(sparklineSource.rows).map((b) => ({
    label: b.label,
    value: b.value,
  }));

  // Overspend alert: today's spend vs. 7-day mean
  const todayLabel = (() => {
    const d = new Date();
    return `${d.getMonth() + 1}/${d.getDate()}`;
  })();
  const todayBucket = sparklineItems.find((b) => b.label === todayLabel);
  const todaySpend = todayBucket?.value ?? 0;
  const dailyValues = sparklineItems.map((b) => b.value);
  const dailyMean =
    dailyValues.length > 0
      ? dailyValues.reduce((a, b) => a + b, 0) / dailyValues.length
      : 0;
  const showOverspend = todaySpend > dailyMean && dailyMean > 0;

  // Build unique agents present in rows for badges
  const uniqueAgents: Map<string, string> = new Map();
  if (data.view === "detail") {
    for (const row of data.rows) {
      if (isCostRow(row)) {
        uniqueAgents.set(row.agent, row.agent_label);
      }
    }
  }

  // Build table data
  let tableElement: React.JSX.Element;

  if (data.view === "grouped") {
    const groupedRows = data.rows as CostGroupRow[];
    const tableData: TableRowGrouped[] = groupedRows.map((r) => ({
      group: r.key_label,
      sessions: String(r.session_count),
      tokens: r.tokens.total_tokens_display,
      cost: r.cost_display,
    }));
    tableElement = (
      <Table<TableRowGrouped>
        data={tableData}
        columns={[
          { key: "group", header: "Group", width: 20 },
          { key: "sessions", header: "Sessions", width: 10, align: "right" },
          { key: "tokens", header: "Tokens", width: 14, align: "right" },
          { key: "cost", header: "Cost", width: 12, align: "right" },
        ]}
        maxRows={25}
      />
    );
  } else {
    const detailRows = data.rows as CostRow[];
    const tableData: TableRowDetail[] = detailRows.map((r) => ({
      date: r.date_display,
      agent: r.agent_label,
      project: r.project.length > 18 ? r.project.slice(0, 16) + "…" : r.project,
      model: r.model.length > 20 ? r.model.slice(0, 18) + "…" : r.model,
      cost: r.cost_display,
      tokens: r.tokens.total_tokens_display,
    }));
    tableElement = (
      <Table<TableRowDetail>
        data={tableData}
        columns={[
          { key: "date", header: "Date", width: 10 },
          { key: "agent", header: "Agent", width: 16 },
          { key: "project", header: "Project", width: 18 },
          { key: "model", header: "Model", width: 20 },
          { key: "tokens", header: "Tokens", width: 14, align: "right" },
          { key: "cost", header: "Cost", width: 12, align: "right" },
        ]}
        maxRows={25}
      />
    );
  }

  const sparklineChartData = sparklineItems.map((b) => ({
    label: b.label,
    value: b.value,
    color: undefined as string | undefined,
  }));

  return (
    <Box flexDirection="column" gap={1}>
      {/* Header */}
      <Box flexDirection="column">
        <Text bold>
          Cost — {data.period}
          {groupBy ? `  [grouped by ${groupBy}]` : ""}
        </Text>
        <Text>
          {data.totals.session_count} session{data.totals.session_count !== 1 ? "s" : ""}
          {"  "}
          {data.totals.tokens.total_tokens_display} tokens
          {"  "}
          <Text bold>{data.totals.cost_display}</Text>
        </Text>
      </Box>

      {/* Agent badges (detail mode only) */}
      {uniqueAgents.size > 0 && (
        <Box flexDirection="row" gap={1} flexWrap="wrap">
          {Array.from(uniqueAgents.entries()).map(([agent, label]) => (
            <Badge key={agent} variant={agentVariant(agent)}>
              {label}
            </Badge>
          ))}
        </Box>
      )}

      {/* 7-day sparkline */}
      <BarChart
        data={sparklineChartData}
        direction="horizontal"
        width={50}
        showValues={true}
        title="7-day spending"
      />

      {/* Overspend warning */}
      {showOverspend && (
        <Alert variant="warning" title="Spending alert">
          {"Today's spend (" +
            fmtUsd(todaySpend) +
            ") is above the 7-day average (" +
            fmtUsd(dailyMean) +
            ")"}
        </Alert>
      )}

      {/* Main breakdown table */}
      {tableElement}

      {/* Export feedback */}
      {exporting && <Spinner label="Exporting…" />}
      {exportResult && (
        <Alert variant="success" title="Export complete">
          {exportResult}
        </Alert>
      )}
      {exportError && (
        <Alert variant="error" title="Export failed">
          {exportError}
        </Alert>
      )}

      {/* Footer hints */}
      <Box flexDirection="row" gap={2}>
        <Text dimColor>
          Period: 1=today 2=weekly 3=monthly 4=all  p=cycle
        </Text>
        <Text dimColor>g=toggle grouping</Text>
        <Text dimColor>E=export CSV  J=export JSON</Text>
      </Box>
    </Box>
  );
}
