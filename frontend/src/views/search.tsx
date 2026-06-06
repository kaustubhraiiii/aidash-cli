import { useEffect, useState } from "react";
import { Box, Text } from "ink";
import { runEngine, EngineError } from "../engine.js";
import { Spinner, Alert } from "@/components";
import type { SearchData } from "../types/index.js";

export function SearchView({ args }: { args: string[] }) {
  const [data, setData] = useState<SearchData | null>(null);
  const [error, setError] = useState<EngineError | null>(null);

  useEffect(() => {
    runEngine<SearchData>("search", args)
      .then((env) => setData(env.data))
      .catch((e) => setError(e as EngineError));
  }, []);

  if (error)
    return (
      <Alert variant="error" title="aidash error">
        {error.message}
      </Alert>
    );
  if (!data) return <Spinner label="Searching…" />;
  if (data.empty)
    return (
      <Alert variant="warning" title="No sessions matched">
        {data.empty.suggestion}
      </Alert>
    );

  return (
    <Box flexDirection="column">
      <Text bold>Search — {data.query}</Text>
      <Text>{data.result_count} results</Text>
    </Box>
  );
}
