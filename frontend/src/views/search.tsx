import React, { useEffect, useState } from "react";
import { Box, Text } from "ink";
import { runEngine, EngineError } from "../engine.js";
import type { SearchData } from "../types/index.js";

export function SearchView({ args }: { args: string[] }) {
  const [data, setData] = useState<SearchData | null>(null);
  const [error, setError] = useState<EngineError | null>(null);

  useEffect(() => {
    runEngine<SearchData>("search", args)
      .then((env) => setData(env.data))
      .catch((e) => setError(e as EngineError));
  }, []);

  if (error) return <Text color="red">aidash error: {error.message}</Text>;
  if (!data) return <Text>Searching…</Text>;
  if (data.empty) return <Text color="yellow">{data.empty.suggestion}</Text>;

  return (
    <Box flexDirection="column">
      <Text bold>Search — {data.query}</Text>
      <Text>{data.result_count} results</Text>
    </Box>
  );
}
