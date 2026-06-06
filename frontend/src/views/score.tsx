import React, { useEffect, useState } from "react";
import { Box, Text } from "ink";
import { runEngine, EngineError } from "../engine.js";
import type { ScoreData } from "../types/index.js";

export function ScoreView({ args }: { args: string[] }) {
  const [data, setData] = useState<ScoreData | null>(null);
  const [error, setError] = useState<EngineError | null>(null);

  useEffect(() => {
    runEngine<ScoreData>("score", args)
      .then((env) => setData(env.data))
      .catch((e) => setError(e as EngineError));
  }, []);

  if (error) return <Text color="red">aidash error: {error.message}</Text>;
  if (!data) return <Text>Loading score…</Text>;
  if (data.empty) return <Text color="yellow">{data.empty.suggestion}</Text>;

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
