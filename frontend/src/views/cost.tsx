import React, { useEffect, useState } from "react";
import { Box, Text } from "ink";
import { runEngine, EngineError } from "../engine.js";
import type { CostData } from "../types/index.js";

export function CostView({ args }: { args: string[] }) {
  const [data, setData] = useState<CostData | null>(null);
  const [error, setError] = useState<EngineError | null>(null);

  useEffect(() => {
    runEngine<CostData>("cost", args)
      .then((env) => setData(env.data))
      .catch((e) => setError(e as EngineError));
  }, []);

  if (error) return <Text color="red">aidash error: {error.message}</Text>;
  if (!data) return <Text>Loading cost…</Text>;
  if (data.empty) return <Text color="yellow">{data.empty.suggestion}</Text>;

  return (
    <Box flexDirection="column">
      <Text bold>Cost — {data.period}</Text>
      <Text>
        {data.totals.session_count} sessions · {data.totals.cost_display}
      </Text>
    </Box>
  );
}
