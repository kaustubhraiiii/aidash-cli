import React, { useEffect, useState } from "react";
import { Box, Text } from "ink";
import { runEngine, EngineError } from "../engine.js";
import type { ReplayData } from "../types/index.js";

export function ReplayView({ args }: { args: string[] }) {
  const [data, setData] = useState<ReplayData | null>(null);
  const [error, setError] = useState<EngineError | null>(null);

  useEffect(() => {
    runEngine<ReplayData>("replay", args)
      .then((env) => setData(env.data))
      .catch((e) => setError(e as EngineError));
  }, []);

  if (error) return <Text color="red">aidash error: {error.message}</Text>;
  if (!data) return <Text>Loading replay…</Text>;
  if (data.empty) return <Text color="yellow">{data.empty.suggestion}</Text>;

  return (
    <Box flexDirection="column">
      <Text bold>Replay — {data.target}</Text>
      <Text>{data.sessions.length} sessions</Text>
    </Box>
  );
}
