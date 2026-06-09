import { spawn } from "node:child_process";
import { writeFile } from "node:fs/promises";
import { join } from "node:path";
import type { CommandName, Envelope } from "./types/index.js";
import type {
  CostData,
  ReplayData,
  ScoreData,
  RatesData,
  SearchData,
} from "./types/index.js";

// ---------------------------------------------------------------------------
// Error kind & suggestion map
// ---------------------------------------------------------------------------

/** Distinct, typed failure modes for the Python subprocess. */
export type EngineErrorKind =
  | "python_not_found" // spawn ENOENT — no python on PATH
  | "aidash_not_installed" // python ran but module aidash missing
  | "nonzero_exit" // process exited non-zero for another reason
  | "bad_json" // stdout was not parseable JSON
  | "envelope_error"; // valid JSON, but ok:false

const SUGGESTIONS: Record<EngineErrorKind, string> = {
  python_not_found:
    "Install Python 3 and ensure it is on PATH, or set AIDASH_PYTHON.",
  aidash_not_installed:
    "Run pip install aidash to install the engine.",
  nonzero_exit:
    "Run python3 -m aidash <command> --json manually to see the underlying error.",
  bad_json:
    "The engine returned malformed output — upgrade with pip install -U aidash.",
  envelope_error:
    "The engine reported an error — check the message and code fields for details.",
};

export class EngineError extends Error {
  readonly suggestion: string;

  constructor(
    readonly kind: EngineErrorKind,
    message: string,
    readonly detail?: { exitCode?: number | null; stderr?: string; code?: string },
  ) {
    super(message);
    this.name = "EngineError";
    // For envelope_error the suggestion may reference engine's own code/message,
    // but we keep a sensible default here; callers can inspect detail.code.
    this.suggestion =
      kind === "envelope_error" && detail?.code
        ? `Engine error code: ${detail.code}. ${SUGGESTIONS.envelope_error}`
        : SUGGESTIONS[kind];
  }
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const PYTHON_BIN = process.env.AIDASH_PYTHON ?? "python3";

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function looksLikeMissingModule(stderr: string): boolean {
  return (
    /No module named ['"]?aidash/.test(stderr) ||
    /ModuleNotFoundError: No module named ['"]?aidash/.test(stderr)
  );
}

/**
 * Low-level spawn helper. Resolves with { stdout, stderr, exitCode } on clean
 * exit (exit code 0 for the --json path; callers decide what to do with
 * nonzero exits for the raw path). Rejects with a typed EngineError only for
 * spawn-level failures (ENOENT, etc.).
 */
function runRaw(
  argv: string[],
): Promise<{ stdout: string; stderr: string; exitCode: number | null }> {
  return new Promise((resolve, reject) => {
    let child;
    try {
      child = spawn(PYTHON_BIN, argv, { stdio: ["ignore", "pipe", "pipe"] });
    } catch (err) {
      reject(
        new EngineError(
          "python_not_found",
          `Could not start Python ("${PYTHON_BIN}"). Is Python installed?`,
          { stderr: String(err) },
        ),
      );
      return;
    }

    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (c: Buffer) => {
      stdout += c;
    });
    child.stderr.on("data", (c: Buffer) => {
      stderr += c;
    });

    child.on("error", (err: NodeJS.ErrnoException) => {
      if (err.code === "ENOENT") {
        reject(
          new EngineError(
            "python_not_found",
            `Python executable "${PYTHON_BIN}" not found on PATH. ` +
              `Set AIDASH_PYTHON to override.`,
            { stderr: err.message },
          ),
        );
      } else {
        reject(
          new EngineError("nonzero_exit", err.message, { stderr: err.message }),
        );
      }
    });

    child.on("close", (exitCode) => {
      resolve({ stdout, stderr, exitCode });
    });
  });
}

/**
 * Map a nonzero-exit subprocess result to a typed EngineError. Shared between
 * the envelope path and the raw export path.
 */
function mapNonzeroExit(
  command: string,
  exitCode: number | null,
  stderr: string,
): EngineError {
  if (looksLikeMissingModule(stderr)) {
    return new EngineError(
      "aidash_not_installed",
      `The "aidash" Python package is not installed in ${PYTHON_BIN}. ` +
        `Run: pip install aidash`,
      { exitCode, stderr },
    );
  }
  return new EngineError(
    "nonzero_exit",
    `aidash ${command} exited with code ${exitCode}.`,
    { exitCode, stderr },
  );
}

// ---------------------------------------------------------------------------
// Core runEngine (kept intact — existing views depend on this)
// ---------------------------------------------------------------------------

/**
 * Spawn `python -m aidash <command> --json [...args]`, parse stdout as a typed
 * envelope, and translate every failure into an {@link EngineError}.
 */
export function runEngine<T>(
  command: CommandName,
  args: string[] = [],
): Promise<Envelope<T>> {
  const argv = ["-m", "aidash", command, ...args, "--json"];
  return runRaw(argv).then(({ stdout, stderr, exitCode }) => {
    if (exitCode !== 0) {
      throw mapNonzeroExit(command, exitCode, stderr);
    }

    let parsed: Envelope<T>;
    try {
      parsed = JSON.parse(stdout) as Envelope<T>;
    } catch {
      throw new EngineError(
        "bad_json",
        `Could not parse JSON from "aidash ${command}".`,
        { exitCode, stderr: stderr || stdout.slice(0, 500) },
      );
    }

    if (!parsed.ok) {
      throw new EngineError(
        "envelope_error",
        parsed.error?.message ?? "aidash reported an error.",
        { exitCode, code: parsed.error?.code },
      );
    }

    return parsed;
  });
}

// ---------------------------------------------------------------------------
// Per-command typed Options interfaces & result type aliases
// ---------------------------------------------------------------------------

export interface CostOptions {
  period?: "today" | "weekly" | "monthly" | "all";
  by?: "agent" | "project" | "model";
  agent?: string;
}

export interface ReplayOptions {
  target?: string;
}

export interface ScoreOptions {
  target?: string;
  trend?: boolean;
}

export interface RatesOptions {
  period?: "weekly" | "monthly" | "all"; // rates CLI does not support "today"
  compare?: boolean;
}

export interface SearchOptions {
  query: string;
  agent?: string;
  project?: string;
  limit?: number;
}

export type CostResult = CostData;
export type ReplayResult = ReplayData;
export type ScoreResult = ScoreData;
export type RatesResult = RatesData;
export type SearchResult = SearchData;

// ---------------------------------------------------------------------------
// Internal helper: unwrap envelope.data (ok:true guarantees data is non-null
// per the engine contract, but we guard defensively).
// ---------------------------------------------------------------------------

function unwrap<T>(envelope: Envelope<T>, command: string): T {
  if (envelope.data === null) {
    throw new EngineError(
      "envelope_error",
      `aidash ${command} returned ok:true but data was null.`,
    );
  }
  return envelope.data;
}

// ---------------------------------------------------------------------------
// Per-command typed wrappers
// ---------------------------------------------------------------------------

/** Fetch cost data. Empty results (no matching sessions) are returned, not thrown. */
export function runCost(opts: CostOptions = {}): Promise<CostResult> {
  const args: string[] = [];
  if (opts.period !== undefined) args.push("--period", opts.period);
  if (opts.by !== undefined) args.push("--by", opts.by);
  if (opts.agent !== undefined) args.push("--agent", opts.agent);
  return runEngine<CostData>("cost", args).then((env) => unwrap(env, "cost"));
}

/** Fetch replay data for a session. */
export function runReplay(opts: ReplayOptions = {}): Promise<ReplayResult> {
  const args: string[] = [];
  if (opts.target !== undefined) args.push(opts.target);
  return runEngine<ReplayData>("replay", args).then((env) =>
    unwrap(env, "replay"),
  );
}

/** Fetch score data for a session, optionally with trend. */
export function runScore(opts: ScoreOptions = {}): Promise<ScoreResult> {
  const args: string[] = [];
  if (opts.target !== undefined) args.push(opts.target);
  if (opts.trend === true) args.push("--trend");
  return runEngine<ScoreData>("score", args).then((env) =>
    unwrap(env, "score"),
  );
}

/** Fetch rate data, optionally with model comparison. */
export function runRates(opts: RatesOptions = {}): Promise<RatesResult> {
  const args: string[] = [];
  if (opts.period !== undefined) args.push("--period", opts.period);
  if (opts.compare === true) args.push("--compare");
  return runEngine<RatesData>("rates", args).then((env) =>
    unwrap(env, "rates"),
  );
}

/** Search sessions by query text. */
export function runSearch(opts: SearchOptions): Promise<SearchResult> {
  const args: string[] = [opts.query];
  if (opts.agent !== undefined) args.push("--agent", opts.agent);
  if (opts.project !== undefined) args.push("--project", opts.project);
  if (opts.limit !== undefined) args.push("--limit", String(opts.limit));
  return runEngine<SearchData>("search", args).then((env) =>
    unwrap(env, "search"),
  );
}

// ---------------------------------------------------------------------------
// Export helper (raw spawn — mutually exclusive with --json)
// ---------------------------------------------------------------------------

export interface ExportResult {
  path: string;
  format: "csv" | "json";
  bytes: number;
}

/**
 * Spawn `python -m aidash cost [...flags] --export <format>` (NO --json flag).
 * Captures raw stdout (csv or json text), writes it to a timestamped file in
 * process.cwd(), and returns the absolute path + byte count.
 */
export async function exportCost(
  opts: CostOptions,
  format: "csv" | "json",
): Promise<ExportResult> {
  const args: string[] = ["-m", "aidash", "cost"];
  if (opts.period !== undefined) args.push("--period", opts.period);
  if (opts.by !== undefined) args.push("--by", opts.by);
  if (opts.agent !== undefined) args.push("--agent", opts.agent);
  args.push("--export", format);

  const { stdout, stderr, exitCode } = await runRaw(args);

  if (exitCode !== 0) {
    throw mapNonzeroExit("cost --export", exitCode, stderr);
  }

  const period = opts.period ?? "all";
  const timestamp = Date.now();
  const filename = `aidash-cost-${period}-${timestamp}.${format}`;
  const filePath = join(process.cwd(), filename);

  const bytes = Buffer.byteLength(stdout, "utf8");
  await writeFile(filePath, stdout, "utf8");

  return { path: filePath, format, bytes };
}
