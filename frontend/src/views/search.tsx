import { useEffect, useState } from "react";
import { Box, Text } from "ink";
import { default as SelectInput } from "ink-select-input";
import { runSearch, EngineError } from "../engine.js";
import { Spinner, Alert, Badge } from "@/components";
import { useInput } from "@/hooks/use-input";
import type { SearchData, SearchRow } from "../types/index.js";

function parseArgs(args: string[]): {
  query: string;
  agentFilter: string | undefined;
  projectFilter: string | undefined;
  limit: number;
} {
  let query = "";
  let agentFilter: string | undefined;
  let projectFilter: string | undefined;
  let limit = 10;

  let i = 0;
  while (i < args.length) {
    const arg = args[i];
    if (arg === "--agent" && i + 1 < args.length) {
      agentFilter = args[i + 1];
      i += 2;
    } else if (arg === "--project" && i + 1 < args.length) {
      projectFilter = args[i + 1];
      i += 2;
    } else if (arg === "--limit" && i + 1 < args.length) {
      const parsed = parseInt(args[i + 1] ?? "", 10);
      if (!isNaN(parsed)) {
        limit = parsed;
      }
      i += 2;
    } else if (arg !== undefined && !arg.startsWith("--")) {
      if (query === "") {
        query = arg;
      }
      i += 1;
    } else {
      i += 1;
    }
  }

  return { query, agentFilter, projectFilter, limit };
}

interface SelectItem {
  label: string;
  value: string;
  key: string;
}

function PreviewSegments({ row }: { row: SearchRow }): React.JSX.Element {
  return (
    <Box flexDirection="row" flexWrap="wrap">
      {row.preview_segments.map((seg, idx) =>
        seg.match ? (
          <Text key={idx} bold color="yellow">
            {seg.text}
          </Text>
        ) : (
          <Text key={idx}>{seg.text}</Text>
        )
      )}
    </Box>
  );
}

function DetailView({
  row,
  onBack,
}: {
  row: SearchRow;
  onBack: () => void;
}): React.JSX.Element {
  useInput((input, key) => {
    if (input === "q" || key.escape) {
      onBack();
    }
  });

  return (
    <Box flexDirection="column" gap={1}>
      <Text bold>Session detail</Text>
      <Box flexDirection="column">
        <Text>
          <Text bold>session_id: </Text>
          {row.session_id}
        </Text>
        <Box flexDirection="row" gap={2}>
          <Text>
            <Text bold>agent: </Text>
            {row.agent_label}
          </Text>
          <Text>
            <Text bold>date: </Text>
            {row.date_display}
          </Text>
        </Box>
        <Text>
          <Text bold>project: </Text>
          {row.project}
        </Text>
        <Box flexDirection="row" gap={2}>
          <Text>
            <Text bold>cost: </Text>
            {row.cost_display}
          </Text>
          <Text>
            <Text bold>tokens: </Text>
            {row.tokens.total_tokens_display}
          </Text>
        </Box>
      </Box>
      <PreviewSegments row={row} />
      <Text dimColor>{"Run: aidash replay " + row.session_id_short + "  to open"}</Text>
      <Text dimColor>{"q/Escape = back to list"}</Text>
    </Box>
  );
}

export function SearchView({ args }: { args: string[] }): React.JSX.Element {
  const { query, agentFilter, projectFilter, limit } = parseArgs(args);

  const [data, setData] = useState<SearchData | null>(null);
  const [error, setError] = useState<EngineError | null>(null);
  const [highlightedId, setHighlightedId] = useState<string | null>(null);
  const [selectedRow, setSelectedRow] = useState<SearchRow | null>(null);

  useEffect(() => {
    if (query === "") return;
    runSearch({ query, agent: agentFilter, project: projectFilter, limit })
      .then((result) => {
        setData(result);
      })
      .catch((e: unknown) => {
        setError(e as EngineError);
      });
  }, []);

  useInput(
    (input, _key) => {
      if (input === "q") {
        process.exit(0);
      }
    },
    { isActive: selectedRow === null }
  );

  if (query === "") {
    return (
      <Alert variant="warning" title="No query">
        {"Provide a search query: aidash search <query>"}
      </Alert>
    );
  }

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

  if (data === null) {
    return <Spinner label="Loading search…" />;
  }

  if (data.empty !== null) {
    return (
      <Box flexDirection="column" gap={1}>
        <Alert variant="warning">{data.empty.suggestion}</Alert>
        {data.empty.detected_agents.map((a) => (
          <Badge key={a.agent}>{a.agent_label}</Badge>
        ))}
      </Box>
    );
  }

  if (selectedRow !== null) {
    return (
      <DetailView
        row={selectedRow}
        onBack={() => setSelectedRow(null)}
      />
    );
  }

  const items: SelectItem[] = data.rows.map((r) => ({
    label:
      "[" +
      r.session_id_short +
      "] " +
      r.agent_label +
      "  " +
      r.date_display +
      "  (" +
      r.match_count +
      " match" +
      (r.match_count !== 1 ? "es" : "") +
      ")" +
      "  " +
      (r.preview.length > 50 ? r.preview.slice(0, 48) + "…" : r.preview),
    value: r.session_id,
    key: r.session_id,
  }));

  const activeId = highlightedId ?? (data.rows[0]?.session_id ?? null);
  const previewRow =
    data.rows.find((r) => r.session_id === activeId) ?? data.rows[0] ?? null;

  return (
    <Box flexDirection="column" gap={1}>
      <Box flexDirection="row" gap={1} flexWrap="wrap">
        <Text bold>
          {"Search: " +
            data.query +
            "  " +
            data.result_count +
            " result" +
            (data.result_count !== 1 ? "s" : "")}
        </Text>
        {agentFilter !== undefined && (
          <Badge variant="info">{"agent: " + agentFilter}</Badge>
        )}
        {projectFilter !== undefined && (
          <Badge variant="secondary">{"project: " + projectFilter}</Badge>
        )}
      </Box>

      <SelectInput
        items={items}
        onHighlight={(item: { label: string; value: string }) =>
          setHighlightedId(item.value)
        }
        onSelect={(item: { label: string; value: string }) => {
          const row =
            data.rows.find((r) => r.session_id === item.value) ?? null;
          setSelectedRow(row);
        }}
        limit={Math.min(items.length, 8)}
      />

      {previewRow !== null && <PreviewSegments row={previewRow} />}

      <Text dimColor>{"↑↓ navigate   Enter select   q quit"}</Text>
    </Box>
  );
}
