import { useEffect, useState } from "react";
import { Box, Text } from "ink";
import { runEngine, EngineError } from "../engine.js";
import { Spinner, Alert } from "@/components";
import type { CostData } from "../types/index.js";

export function CostView({ args }: { args: string[] }) {
  const [data, setData] = useState<CostData | null>(null);
  const [error, setError] = useState<EngineError | null>(null);

  useEffect(() => {
    runEngine<CostData>("cost", args)
      .then((env) => setData(env.data))
      .catch((e) => setError(e as EngineError));
  }, []);

  if (error)
    return (
      <Alert variant="error" title="aidash error">
        {error.message}
      </Alert>
    );
  if (!data) return <Spinner label="Loading cost…" />;
  if (data.empty)
    return (
      <Alert variant="warning" title="No sessions matched">
        {data.empty.suggestion}
      </Alert>
    );

  return (
    <Box flexDirection="column">
      <Text bold>Cost — {data.period}</Text>
      <Text>
        {data.totals.session_count} sessions · {data.totals.cost_display}
      </Text>
    </Box>
  );
}
