import { useEffect, useState } from "react";
import { Box, Text } from "ink";
import { runEngine, EngineError } from "../engine.js";
import { Spinner, Alert } from "@/components";
import type { ScoreData } from "../types/index.js";

export function ScoreView({ args }: { args: string[] }) {
  const [data, setData] = useState<ScoreData | null>(null);
  const [error, setError] = useState<EngineError | null>(null);

  useEffect(() => {
    runEngine<ScoreData>("score", args)
      .then((env) => setData(env.data))
      .catch((e) => setError(e as EngineError));
  }, []);

  if (error)
    return (
      <Alert variant="error" title="aidash error">
        {error.message}
      </Alert>
    );
  if (!data) return <Spinner label="Loading score…" />;
  if (data.empty)
    return (
      <Alert variant="warning" title="No sessions matched">
        {data.empty.suggestion}
      </Alert>
    );

  return (
    <Box flexDirection="column">
      <Text bold>Score — {data.view}</Text>
      <Text>
        {data.view === "trend"
          ? `${data.weeks.length} weeks`
          : `${data.sessions.length} scored`}
      </Text>
    </Box>
  );
}
