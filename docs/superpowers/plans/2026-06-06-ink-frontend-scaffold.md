# Ink/TS Frontend Monorepo Scaffold — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold an npm-workspace monorepo that adds an Ink/TypeScript frontend (`frontend/`) which drives the untouched Python `aidash` engine over a JSON subprocess contract.

**Architecture:** Root `package.json` declares npm workspaces `["frontend"]`. The Python package stays exactly as-is. `frontend/` is a TypeScript ESM project: `cli.tsx` parses argv and routes to one Ink view per command; `engine.ts` spawns `python -m aidash <cmd> --json`, parses stdout as a typed `Envelope<T>`, and surfaces typed errors for the three failure modes (Python missing, aidash missing, non-zero exit). Contract interfaces live in `frontend/src/types/`. A `.claude-plugin/` + `commands/` tree registers the tool as a Claude Code plugin.

**Tech Stack:** TypeScript (strict, ESNext, `moduleResolution: bundler`), Ink + React, termcn component wrappers, npm workspaces. Python side: 3.10+ (unchanged).

**Hard constraints (from the task):**
- Do NOT modify or remove any existing Python file (`aidash/**`, `pyproject.toml`, `test_claude_parser.py`).
- TypeScript strict mode ON.
- `engine.ts` must have typed handling for: Python not installed, `aidash` not installed/importable, and non-zero exit codes.
- After scaffolding, run the test suite to verify nothing broke.

**Known follow-ups (out of scope here, documented so the scaffold is honest):**
- `python -m aidash` needs an `aidash/__main__.py` and a `--json` flag — both land in the later *Python JSON phase*. The scaffold writes the spawn call as specified; it will return data once that phase ships.
- `ARCHITECTURE.md` is not finalized; `types/` is seeded from the envelope contract (Envelope/Meta/ErrorInfo/Tokens/EmptyState/ExportBlock) and per-command interface stubs, to be reconciled with ARCHITECTURE.md when it lands.

---

## File Structure

```
package.json                      # NEW root workspace (private, workspaces:["frontend"])
.gitignore                        # MODIFY: append node_modules/, dist/, *.tsbuildinfo
frontend/
  package.json                    # NEW name:aidash, bin:{aidash-ui:./dist/cli.js}, type:module
  tsconfig.json                   # NEW strict, ESNext, moduleResolution:bundler
  src/
    cli.tsx                       # NEW entry: shebang, argv parse, route to view
    engine.ts                     # NEW subprocess wrapper + typed errors
    views/{cost,replay,score,rates,search}.tsx   # NEW one view per command
    components/index.ts           # NEW shared termcn wrappers barrel
    types/
      envelope.ts                 # NEW Envelope<T>, Meta, ErrorInfo, Tokens, EmptyState, ExportBlock, rating
      cost.ts replay.ts score.ts rates.ts search.ts   # NEW per-command data interfaces
      index.ts                    # NEW barrel re-export
.claude-plugin/
  plugin.json                     # NEW plugin manifest
  marketplace.json                # NEW marketplace manifest
commands/
  cost.md replay.md score.md rates.md search.md       # NEW empty slash-command stubs
```

Existing `aidash/`, `pyproject.toml`, `README.md`, `LICENSE`, `test_claude_parser.py` are **untouched**.

---

### Task 1: Root workspace + gitignore

**Files:**
- Create: `package.json`
- Modify: `.gitignore` (append)

- [ ] **Step 1: Create root `package.json`**

```json
{
  "name": "aidash-monorepo",
  "private": true,
  "version": "0.2.0",
  "description": "aidash — Python engine + Ink/TS frontend monorepo",
  "workspaces": ["frontend"],
  "scripts": {
    "build": "npm run build --workspace=frontend",
    "dev": "npm run dev --workspace=frontend",
    "typecheck": "npm run typecheck --workspace=frontend"
  },
  "license": "MIT"
}
```

- [ ] **Step 2: Append Node ignores to `.gitignore`**

Append these lines (do not remove existing Python entries):

```
# Node / frontend
node_modules/
frontend/dist/
*.tsbuildinfo
```

- [ ] **Step 3: Commit**

```bash
git add package.json .gitignore
git commit -m "chore: add root npm workspace for monorepo"
```

---

### Task 2: frontend package.json + tsconfig + dependency install

**Files:**
- Create: `frontend/package.json`, `frontend/tsconfig.json`

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "aidash",
  "version": "0.2.0",
  "description": "Ink/TypeScript frontend for aidash",
  "type": "module",
  "bin": { "aidash-ui": "./dist/cli.js" },
  "files": ["dist"],
  "scripts": {
    "build": "tsc",
    "dev": "tsc --watch",
    "typecheck": "tsc --noEmit",
    "start": "node dist/cli.js"
  },
  "engines": { "node": ">=18" },
  "license": "MIT"
}
```

- [ ] **Step 2: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ESNext",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "lib": ["ESNext"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "declaration": true,
    "resolveJsonModule": true
  },
  "include": ["src/**/*"],
  "exclude": ["dist", "node_modules"]
}
```

- [ ] **Step 3: Install runtime deps** (run from repo root so workspace hoisting applies)

```bash
npm install --workspace=frontend \
  ink react ink-table ink-spinner ink-select-input ink-chart ink-scroll-view \
  @termcn/table @termcn/bar-chart @termcn/spinner @termcn/alert @termcn/badge
```

Expected: packages resolve and install. **If any package 404s** (notably `ink-chart`, `ink-scroll-view`, `@termcn/*` may not exist on the registry), record the exact failing names, continue installing the rest, and report them in the final summary. Do NOT invent replacements.

- [ ] **Step 4: Install dev deps (types + tsx runner)**

```bash
npm install --workspace=frontend -D \
  typescript @types/react @types/node tsx
```

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/tsconfig.json package-lock.json package.json
git commit -m "build: scaffold frontend package with ink + termcn deps"
```

---

### Task 3: Contract types (`types/`)

**Files:**
- Create: `frontend/src/types/envelope.ts`, `cost.ts`, `replay.ts`, `score.ts`, `rates.ts`, `search.ts`, `index.ts`

- [ ] **Step 1: Create `frontend/src/types/envelope.ts`**

```ts
// Shared JSON contract primitives. Mirrors the envelope in ARCHITECTURE.md.
export type CommandName = "cost" | "replay" | "score" | "rates" | "search";
export type ErrorCode = "bad_argument" | "session_not_found" | "parse_error" | "internal";
export type Rating = "good" | "ok" | "poor";

export interface ErrorInfo {
  code: ErrorCode;
  message: string;
}

export interface Meta {
  generated_at: string;            // ISO 8601
  aidash_version: string;
  period: string | null;
  filters: Record<string, string | null>;
}

export interface Envelope<T> {
  schema_version: string;          // "1.0"
  command: CommandName;
  ok: boolean;
  data: T | null;
  error: ErrorInfo | null;
  meta: Meta;
}

export interface Tokens {
  input_tokens: number;            input_tokens_display: string;
  output_tokens: number;           output_tokens_display: string;
  cache_read_tokens: number;       cache_read_tokens_display: string;
  cache_creation_tokens: number;   cache_creation_tokens_display: string;
  total_tokens: number;            total_tokens_display: string;
}

export interface DetectedAgent {
  agent: string;
  agent_label: string;
  sessions: number;
}

export interface EmptyState {
  active_filters: Record<string, string>;
  detected_agents: DetectedAgent[];
  suggestion: string;
}

export interface ExportBlock {
  format: "csv" | "json";
  content: string;
  filename_suggestion: string;
}
```

- [ ] **Step 2: Create `frontend/src/types/cost.ts`**

```ts
import type { Tokens, EmptyState, ExportBlock } from "./envelope.js";

export interface CostRow {
  session_id: string;
  session_id_short: string;
  date: string;
  date_display: string;
  agent: string;
  agent_label: string;
  project: string;
  model: string;
  tokens: Tokens;
  cost_usd: number;
  cost_display: string;
}

export interface CostGroupRow {
  key: string;
  key_label: string;
  session_count: number;
  tokens: Tokens;
  cost_usd: number;
  cost_display: string;
}

export interface CostTotals {
  session_count: number;
  tokens: Tokens;
  cost_usd: number;
  cost_display: string;
}

export interface CostData {
  view: "detail" | "grouped";
  period: string;
  group_by: "agent" | "project" | "model" | null;
  rows: CostRow[] | CostGroupRow[];
  totals: CostTotals;
  empty: EmptyState | null;
  export: ExportBlock | null;
  markdown: string | null;
}
```

- [ ] **Step 3: Create `frontend/src/types/replay.ts`**

```ts
import type { Tokens, EmptyState } from "./envelope.js";

export interface ToolCallInfo {
  name: string;
  timestamp: string | null;
}

export interface ReplayMessage {
  index: number;
  role: "user" | "assistant";
  content_preview: string;
  timestamp: string | null;
  timestamp_display: string;
  elapsed_since_prev_seconds: number | null;
  elapsed_display: string;
  tool_calls: ToolCallInfo[];
  tokens: Tokens | null;
  cost_usd: number;
  cost_display: string;
}

export interface ReplaySession {
  session_id: string;
  session_id_short: string;
  agent: string;
  agent_label: string;
  project: string;
  model: string;
  started_at: string | null;
  started_at_display: string;
  ended_at: string | null;
  ended_at_display: string;
  tokens: Tokens;
  cost_usd: number;
  cost_display: string;
  message_count: number;
  messages: ReplayMessage[];
}

export interface ReplayData {
  target: string;
  sessions: ReplaySession[];
  empty: EmptyState | null;
}
```

- [ ] **Step 4: Create `frontend/src/types/score.ts`**

```ts
import type { EmptyState, Rating } from "./envelope.js";

export interface ScoreMetric {
  key: string;
  label: string;
  raw: number;
  raw_display: string;
  score: number;
  score_display: string;
  weight: number;
  rating: Rating;
}

export interface ScoredSession {
  session_id: string;
  session_id_short: string;
  date: string;
  date_display: string;
  agent: string;
  agent_label: string;
  project: string;
  metrics: ScoreMetric[];
  total_score: number;
  total_display: string;
  verdict: string;
  rating: Rating;
}

export interface TrendWeek {
  week: string;
  avg_score: number;
  avg_display: string;
  session_count: number;
  rating: Rating;
  bar_ratio: number;
}

export interface ScoreData {
  view: "sessions" | "trend";
  target: string;
  sessions: ScoredSession[];
  weeks: TrendWeek[];
  empty: EmptyState | null;
}
```

- [ ] **Step 5: Create `frontend/src/types/rates.ts`**

```ts
import type { EmptyState } from "./envelope.js";

export interface RateRow {
  model: string;
  session_count: number;
  input_per_million_usd: number;
  input_per_million_display: string;
  output_per_million_usd: number;
  output_per_million_display: string;
  avg_cost_per_session_usd: number;
  avg_cost_per_session_display: string;
  io_ratio_pct: number;
  io_ratio_display: string;
  cache_hit_pct: number;
  cache_hit_display: string;
  effective_rate_per_million_usd: number;
  effective_rate_per_million_display: string;
}

export interface RateEstimate {
  comparator: string;
  cost_usd: number;
  cost_display: string;
}

export interface RateComparisonRow {
  agent: string;
  agent_label: string;
  session_count: number;
  actual_cost_usd: number;
  actual_cost_display: string;
  estimates: RateEstimate[];
  cheapest: string;
}

export interface RateComparison {
  comparators: string[];
  rows: RateComparisonRow[];
}

export interface RatesData {
  period: string;
  models: RateRow[];
  comparison: RateComparison | null;
  empty: EmptyState | null;
}
```

- [ ] **Step 6: Create `frontend/src/types/search.ts`**

```ts
import type { Tokens, EmptyState } from "./envelope.js";

export interface PreviewSegment {
  text: string;
  match: boolean;
}

export interface SearchRow {
  rank: number;
  session_id: string;
  session_id_short: string;
  date: string;
  date_display: string;
  agent: string;
  agent_label: string;
  project: string;
  match_count: number;
  preview: string;
  preview_segments: PreviewSegment[];
  tokens: Tokens;
  cost_usd: number;
  cost_display: string;
}

export interface SearchData {
  query: string;
  rows: SearchRow[];
  result_count: number;
  limit: number;
  empty: EmptyState | null;
}
```

- [ ] **Step 7: Create `frontend/src/types/index.ts`**

```ts
export * from "./envelope.js";
export * from "./cost.js";
export * from "./replay.js";
export * from "./score.js";
export * from "./rates.js";
export * from "./search.js";
```

- [ ] **Step 8: Commit**

```bash
git add frontend/src/types
git commit -m "feat(types): add JSON contract interfaces"
```

---

### Task 4: Engine subprocess wrapper (`engine.ts`)

**Files:**
- Create: `frontend/src/engine.ts`

- [ ] **Step 1: Create `frontend/src/engine.ts`**

```ts
import { spawn } from "node:child_process";
import type { CommandName, Envelope } from "./types/index.js";

/** Distinct, typed failure modes for the Python subprocess. */
export type EngineErrorKind =
  | "python_not_found"     // spawn ENOENT — no python on PATH
  | "aidash_not_installed" // python ran but module aidash missing
  | "nonzero_exit"         // process exited non-zero for another reason
  | "bad_json"             // stdout was not parseable JSON
  | "envelope_error";      // valid JSON, but ok:false

export class EngineError extends Error {
  constructor(
    readonly kind: EngineErrorKind,
    message: string,
    readonly detail?: { exitCode?: number | null; stderr?: string; code?: string },
  ) {
    super(message);
    this.name = "EngineError";
  }
}

const PYTHON_BIN = process.env.AIDASH_PYTHON ?? "python3";

function looksLikeMissingModule(stderr: string): boolean {
  return /No module named ['"]?aidash/.test(stderr) ||
    /ModuleNotFoundError: No module named ['"]?aidash/.test(stderr);
}

/**
 * Spawn `python -m aidash <command> --json [...args]`, parse stdout as a typed
 * envelope, and translate every failure into an {@link EngineError}.
 */
export function runEngine<T>(
  command: CommandName,
  args: string[] = [],
): Promise<Envelope<T>> {
  return new Promise((resolve, reject) => {
    const argv = ["-m", "aidash", command, ...args, "--json"];
    let child;
    try {
      child = spawn(PYTHON_BIN, argv, { stdio: ["ignore", "pipe", "pipe"] });
    } catch (err) {
      reject(new EngineError("python_not_found",
        `Could not start Python ("${PYTHON_BIN}"). Is Python installed?`,
        { stderr: String(err) }));
      return;
    }

    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (c) => { stdout += c; });
    child.stderr.on("data", (c) => { stderr += c; });

    child.on("error", (err: NodeJS.ErrnoException) => {
      if (err.code === "ENOENT") {
        reject(new EngineError("python_not_found",
          `Python executable "${PYTHON_BIN}" not found on PATH. ` +
          `Set AIDASH_PYTHON to override.`, { stderr: err.message }));
      } else {
        reject(new EngineError("nonzero_exit", err.message, { stderr: err.message }));
      }
    });

    child.on("close", (exitCode) => {
      if (exitCode !== 0) {
        if (looksLikeMissingModule(stderr)) {
          reject(new EngineError("aidash_not_installed",
            `The "aidash" Python package is not installed in ${PYTHON_BIN}. ` +
            `Run: pip install aidash`, { exitCode, stderr }));
          return;
        }
        reject(new EngineError("nonzero_exit",
          `aidash ${command} exited with code ${exitCode}.`, { exitCode, stderr }));
        return;
      }

      let parsed: Envelope<T>;
      try {
        parsed = JSON.parse(stdout) as Envelope<T>;
      } catch {
        reject(new EngineError("bad_json",
          `Could not parse JSON from "aidash ${command}".`,
          { exitCode, stderr: stderr || stdout.slice(0, 500) }));
        return;
      }

      if (!parsed.ok) {
        reject(new EngineError("envelope_error",
          parsed.error?.message ?? "aidash reported an error.",
          { exitCode, code: parsed.error?.code }));
        return;
      }
      resolve(parsed);
    });
  });
}
```

- [ ] **Step 2: Typecheck**

Run: `npm run typecheck --workspace=frontend`
Expected: PASS (no type errors). If `ink`/`react` type errors appear because a view is not yet written, that's fine at this task — engine.ts alone must compile.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/engine.ts
git commit -m "feat(engine): typed python subprocess wrapper"
```

---

### Task 5: View stubs + components barrel

**Files:**
- Create: `frontend/src/components/index.ts`
- Create: `frontend/src/views/cost.tsx`, `replay.tsx`, `score.tsx`, `rates.tsx`, `search.tsx`

- [ ] **Step 1: Create `frontend/src/components/index.ts`**

```ts
// Shared termcn component wrappers. Thin re-exports for now; views import from here
// so swapping the underlying lib later touches one file.
export { default as Table } from "@termcn/table";
export { default as BarChart } from "@termcn/bar-chart";
export { default as Spinner } from "@termcn/spinner";
export { default as Alert } from "@termcn/alert";
export { default as Badge } from "@termcn/badge";
```

> Note: if a `@termcn/*` package failed to install in Task 2, comment out that single export line and leave a `// TODO(termcn): package unresolved` marker. Record it in the final report.

- [ ] **Step 2: Create each view stub.** Repeat this shape per command, substituting the command name, data type, and `runEngine` call. Full text for `cost.tsx`:

```tsx
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
      <Text>{data.totals.session_count} sessions · {data.totals.cost_display}</Text>
    </Box>
  );
}
```

`replay.tsx` → `runEngine<ReplayData>("replay", args)`, type `ReplayData`, component `ReplayView`.
`score.tsx` → `runEngine<ScoreData>("score", args)`, type `ScoreData`, component `ScoreView`.
`rates.tsx` → `runEngine<RatesData>("rates", args)`, type `RatesData`, component `RatesView`.
`search.tsx` → `runEngine<SearchData>("search", args)`, type `SearchData`, component `SearchView`.

Each stub's render body shows a one-line summary appropriate to its data (e.g. score: `{data.sessions.length} scored`; rates: `{data.models.length} models`; search: `{data.result_count} results`; replay: `{data.sessions.length} sessions`). Keep them minimal — full rendering is a later phase.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components frontend/src/views
git commit -m "feat(views): scaffold one Ink view per command"
```

---

### Task 6: CLI entry + routing (`cli.tsx`)

**Files:**
- Create: `frontend/src/cli.tsx`

- [ ] **Step 1: Create `frontend/src/cli.tsx`**

```tsx
#!/usr/bin/env node
import React from "react";
import { render, Text } from "ink";
import { CostView } from "./views/cost.js";
import { ReplayView } from "./views/replay.js";
import { ScoreView } from "./views/score.js";
import { RatesView } from "./views/rates.js";
import { SearchView } from "./views/search.js";

const VIEWS = {
  cost: CostView,
  replay: ReplayView,
  score: ScoreView,
  rates: RatesView,
  search: SearchView,
} as const;

type Cmd = keyof typeof VIEWS;

function main() {
  const [command, ...args] = process.argv.slice(2);

  if (!command || !(command in VIEWS)) {
    render(
      <Text>
        aidash-ui — usage: aidash-ui &lt;{Object.keys(VIEWS).join(" | ")}&gt; [args]
      </Text>,
    );
    process.exitCode = command ? 1 : 0;
    return;
  }

  const View = VIEWS[command as Cmd];
  render(<View args={args} />);
}

main();
```

- [ ] **Step 2: Build the whole frontend**

Run: `npm run build --workspace=frontend`
Expected: `tsc` completes with no errors; `frontend/dist/cli.js` exists.

- [ ] **Step 3: Smoke-test the binary (usage path, no Python needed)**

Run: `node frontend/dist/cli.js`
Expected: prints the usage line, exits 0.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/cli.tsx
git commit -m "feat(cli): argv routing to per-command Ink views"
```

---

### Task 7: Claude plugin manifests + command stubs

**Files:**
- Create: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`
- Create: `commands/cost.md`, `replay.md`, `score.md`, `rates.md`, `search.md`

- [ ] **Step 1: Create `.claude-plugin/plugin.json`**

```json
{
  "name": "aidash",
  "version": "0.2.0",
  "description": "Track usage, costs, and efficiency across AI coding agents",
  "author": { "name": "Kaustubh Rai", "email": "7899kaustubh@gmail.com" },
  "homepage": "https://github.com/kaustubhraiiii/aidash",
  "commands": "./commands"
}
```

- [ ] **Step 2: Create `.claude-plugin/marketplace.json`**

```json
{
  "name": "aidash",
  "owner": { "name": "Kaustubh Rai" },
  "plugins": [
    {
      "name": "aidash",
      "source": "./",
      "description": "Track usage, costs, and efficiency across AI coding agents"
    }
  ]
}
```

- [ ] **Step 3: Create the five command stubs.** Each `commands/<cmd>.md` is a minimal frontmatter stub:

`commands/cost.md`:

```markdown
---
description: View spending across all AI coding agents
---

Stub — wires to `aidash-ui cost`. To be implemented in a later phase.
```

Repeat for `replay.md` (Play back a session as a timeline), `score.md` (Rate session efficiency), `rates.md` (Compare model pricing), `search.md` (Search across sessions), changing only the `description:` line and the body verb.

- [ ] **Step 4: Commit**

```bash
git add .claude-plugin commands
git commit -m "feat(plugin): add claude plugin manifests and command stubs"
```

---

### Task 8: Verify nothing broke

**Files:** none (verification only)

- [ ] **Step 1: Confirm Python package still imports**

Run: `python3 -c "import aidash; from aidash import cli, loader, scoring, config, models; print('aidash import OK')"`
Expected: prints `aidash import OK`.

- [ ] **Step 2: Run the existing test script**

Run: `python3 test_claude_parser.py`
Expected: runs without traceback. (Output depends on local `~/.claude` data; "0 sessions" is acceptable — a non-zero exit or traceback is a failure.)

- [ ] **Step 3: Confirm no Python file changed**

Run: `git status --porcelain aidash pyproject.toml test_claude_parser.py`
Expected: empty output (no modifications to Python).

- [ ] **Step 4: Confirm frontend typechecks and builds clean**

Run: `npm run typecheck --workspace=frontend && npm run build --workspace=frontend`
Expected: both PASS.

- [ ] **Step 5: Final report**

Summarize: which npm packages installed vs. 404'd, that Python is untouched and imports, and that the frontend builds.

---

## Self-Review

**Spec coverage:** Target tree (root pkg, frontend pkg+tsconfig+src/{cli,engine,views,components,types}, .claude-plugin, commands) — all covered by Tasks 1–7. Dependency list — Task 2. Constraints: no Python edits (verified Task 8 step 3), strict mode (tsconfig Task 2), engine typed errors for the three modes (Task 4: `python_not_found`, `aidash_not_installed`, `nonzero_exit`, plus `bad_json`/`envelope_error`). Run test suite — Task 8.

**Placeholder scan:** Command stubs and views are intentionally minimal but contain complete, compilable content — not "TODO" placeholders. The two documented follow-ups (`__main__.py`/`--json`, ARCHITECTURE.md reconciliation) are explicitly out of scope, not silent gaps.

**Type consistency:** `runEngine<T>(command, args)` signature is identical across all five views. `Envelope<T>`, `EngineError`, and the per-command data interfaces are referenced with consistent names. View prop is uniformly `{ args: string[] }`.

**Risk:** `@termcn/*`, `ink-chart`, `ink-scroll-view` may not exist on npm — handled by Task 2 Step 3 (report, don't substitute) and Task 5 Step 1 (comment out unresolved exports). The components barrel is imported only by views that don't yet use those exports, so a missing package will not block the build if its export line is removed.
