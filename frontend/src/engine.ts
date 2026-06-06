import { spawn } from "node:child_process";
import type { CommandName, Envelope } from "./types/index.js";

/** Distinct, typed failure modes for the Python subprocess. */
export type EngineErrorKind =
  | "python_not_found" // spawn ENOENT — no python on PATH
  | "aidash_not_installed" // python ran but module aidash missing
  | "nonzero_exit" // process exited non-zero for another reason
  | "bad_json" // stdout was not parseable JSON
  | "envelope_error"; // valid JSON, but ok:false

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
  return (
    /No module named ['"]?aidash/.test(stderr) ||
    /ModuleNotFoundError: No module named ['"]?aidash/.test(stderr)
  );
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
    child.stdout.on("data", (c) => {
      stdout += c;
    });
    child.stderr.on("data", (c) => {
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
        reject(new EngineError("nonzero_exit", err.message, { stderr: err.message }));
      }
    });

    child.on("close", (exitCode) => {
      if (exitCode !== 0) {
        if (looksLikeMissingModule(stderr)) {
          reject(
            new EngineError(
              "aidash_not_installed",
              `The "aidash" Python package is not installed in ${PYTHON_BIN}. ` +
                `Run: pip install aidash`,
              { exitCode, stderr },
            ),
          );
          return;
        }
        reject(
          new EngineError(
            "nonzero_exit",
            `aidash ${command} exited with code ${exitCode}.`,
            { exitCode, stderr },
          ),
        );
        return;
      }

      let parsed: Envelope<T>;
      try {
        parsed = JSON.parse(stdout) as Envelope<T>;
      } catch {
        reject(
          new EngineError(
            "bad_json",
            `Could not parse JSON from "aidash ${command}".`,
            { exitCode, stderr: stderr || stdout.slice(0, 500) },
          ),
        );
        return;
      }

      if (!parsed.ok) {
        reject(
          new EngineError(
            "envelope_error",
            parsed.error?.message ?? "aidash reported an error.",
            { exitCode, code: parsed.error?.code },
          ),
        );
        return;
      }
      resolve(parsed);
    });
  });
}
