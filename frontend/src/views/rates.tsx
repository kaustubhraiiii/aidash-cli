import React, { useEffect, useState } from "react";
import { Box, Text } from "ink";
import { runEngine, EngineError } from "../engine.js";
import type { RatesData } from "../types/index.js";

export function RatesView({ args }: { args: string[] }) {
  const [data, setData] = useState<RatesData | null>(null);
  const [error, setError] = useState<EngineError | null>(null);

  useEffect(() => {
    runEngine<RatesData>("rates", args)
      .then((env) => setData(env.data))
      .catch((e) => setError(e as EngineError));
  }, []);

  if (error) return <Text color="red">aidash error: {error.message}</Text>;
  if (!data) return <Text>Loading rates…</Text>;
  if (data.empty) return <Text color="yellow">{data.empty.suggestion}</Text>;

  return (
    <Box flexDirection="column">
      <Text bold>Rates — {data.period}</Text>
      <Text>{data.models.length} models</Text>
    </Box>
  );
}
