import { useEffect, useState } from "react";
import { Box, Text } from "ink";
import { runEngine, EngineError } from "../engine.js";
import { Spinner, Alert } from "@/components";
import type { ReplayData } from "../types/index.js";

export function ReplayView({ args }: { args: string[] }) {
  const [data, setData] = useState<ReplayData | null>(null);
  const [error, setError] = useState<EngineError | null>(null);

  useEffect(() => {
    runEngine<ReplayData>("replay", args)
      .then((env) => setData(env.data))
      .catch((e) => setError(e as EngineError));
  }, []);

  if (error)
    return (
      <Alert variant="error" title="aidash error">
        {error.message}
      </Alert>
    );
  if (!data) return <Spinner label="Loading replay…" />;
  if (data.empty)
    return (
      <Alert variant="warning" title="No sessions matched">
        {data.empty.suggestion}
      </Alert>
    );

  return (
    <Box flexDirection="column">
      <Text bold>Replay — {data.target}</Text>
      <Text>{data.sessions.length} sessions</Text>
    </Box>
  );
}
