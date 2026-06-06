import { useEffect, useState } from "react";
import { Box, Text } from "ink";
import { runEngine, EngineError } from "../engine.js";
import { Spinner, Alert } from "@/components";
import type { RatesData } from "../types/index.js";

export function RatesView({ args }: { args: string[] }) {
  const [data, setData] = useState<RatesData | null>(null);
  const [error, setError] = useState<EngineError | null>(null);

  useEffect(() => {
    runEngine<RatesData>("rates", args)
      .then((env) => setData(env.data))
      .catch((e) => setError(e as EngineError));
  }, []);

  if (error)
    return (
      <Alert variant="error" title="aidash error">
        {error.message}
      </Alert>
    );
  if (!data) return <Spinner label="Loading rates…" />;
  if (data.empty)
    return (
      <Alert variant="warning" title="No sessions matched">
        {data.empty.suggestion}
      </Alert>
    );

  return (
    <Box flexDirection="column">
      <Text bold>Rates — {data.period}</Text>
      <Text>{data.models.length} models</Text>
    </Box>
  );
}
