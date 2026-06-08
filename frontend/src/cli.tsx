import React from "react";
import { render, Box, Text } from "ink";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { EventEmitter } from "node:events";
import minimist from "minimist";
import { ThemeProvider } from "@/components/ui/theme-provider";
import { defaultTheme } from "@/lib/terminal-themes/default";
import { Alert } from "@/components";
import { EngineError, PYTHON_BIN } from "./engine.js";
import { CostView } from "./views/cost.js";
import { ReplayView } from "./views/replay.js";
import { ScoreView } from "./views/score.js";
import { RatesView } from "./views/rates.js";
import { SearchView } from "./views/search.js";
import { HelpView } from "./views/help.js";

// ---------------------------------------------------------------------------
// EngineError boundary
// ---------------------------------------------------------------------------

type EngineErrorBoundaryState = { error: EngineError | null };

class EngineErrorBoundary extends React.Component<
  { children: React.ReactNode },
  EngineErrorBoundaryState
> {
  state: EngineErrorBoundaryState = { error: null };

  static getDerivedStateFromError(e: unknown): EngineErrorBoundaryState {
    if (e instanceof EngineError) return { error: e };
    throw e; // actually propagate to parent
  }

  render(): React.ReactNode {
    if (this.state.error) {
      process.exitCode = 1;
      return (
        <Box flexDirection="column">
          <Alert variant="error" title="aidash error">
            {this.state.error.message}
          </Alert>
          <Text dimColor>{this.state.error.suggestion}</Text>
        </Box>
      );
    }
    return this.props.children;
  }
}

// ---------------------------------------------------------------------------
// App component (exported for testing)
// ---------------------------------------------------------------------------

export function App({ args }: { args: string[] }): React.ReactElement | null {
  // --json passthrough: App should not render anything when --json is in args
  // (the actual bypass happens in main() before render, but if App receives it,
  // return null so the test for --json sees an empty frame)
  if (args.includes("--json")) {
    return null;
  }

  const parsed = minimist(args, {
    boolean: ["json", "trend", "compare"],
    string: ["period", "by", "agent", "project", "limit"],
  });
  const command = parsed._[0] as string | undefined;
  const cmdIndex = command ? args.indexOf(command) : -1;
  const restArgs = cmdIndex >= 0 ? args.slice(cmdIndex + 1) : [];

  let view: React.ReactElement;

  switch (command) {
    case "cost":
      view = <CostView args={restArgs} />;
      break;
    case "replay":
      view = <ReplayView args={restArgs} />;
      break;
    case "score":
      view = <ScoreView args={restArgs} />;
      break;
    case "rates":
      view = <RatesView args={restArgs} />;
      break;
    case "search":
      view = <SearchView args={restArgs} />;
      break;
    default:
      view = <HelpView args={restArgs} />;
      break;
  }

  return (
    <ThemeProvider theme={defaultTheme}>
      <EngineErrorBoundary>{view}</EngineErrorBoundary>
    </ThemeProvider>
  );
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

function main(): void {
  const rawArgs = process.argv.slice(2);

  // --json passthrough: skip Ink entirely
  if (rawArgs.includes("--json")) {
    const jsonParsed = minimist(rawArgs.filter((a) => a !== "--json"));
    const command = (jsonParsed._[0] as string | undefined) ?? "cost";
    const filteredArgs = rawArgs.filter((a) => a !== "--json" && a !== command);
    const result = spawnSync(
      PYTHON_BIN,
      ["-m", "aidash", command, ...filteredArgs, "--json"],
      { stdio: "inherit" },
    );
    process.exit(result.status ?? 1);
    return;
  }

  // When stdin is not a TTY (e.g. piped output), ink's useInput hook throws
  // "Raw mode is not supported". Provide a fake TTY-capable stdin so the
  // useInput hooks can attach without crashing.
  const stdinForRender = process.stdin.isTTY
    ? process.stdin
    : (() => {
        const fake = Object.assign(new EventEmitter(), {
          isTTY: true,
          setEncoding: () => {},
          setRawMode: () => {},
          resume: () => {},
          pause: () => {},
          ref: () => {},
          unref: () => {},
          read: () => null,
          pipe: () => {},
        });
        return fake as unknown as typeof process.stdin;
      })();
  render(<App args={rawArgs} />, { stdin: stdinForRender });
}

// Only run main when this file is the entry point (not when imported in tests).
// Compare the resolved path of this module against process.argv[1].
const __filename = fileURLToPath(import.meta.url);
if (process.argv[1] === __filename) {
  main();
}
