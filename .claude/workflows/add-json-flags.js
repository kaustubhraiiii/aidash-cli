/**
 * add-json-flags.js
 *
 * Workflow descriptor for adding `--json` (and `--export` / `--weekly`) output
 * to the aidash Python engine using parallel subagents.
 *
 * Key design decision: all 5 command implementations live in ONE file
 * (aidash/cli.py) and the tests would collide in one file too. Dispatching 5
 * agents to edit the same files in parallel is unsafe (they clobber each other
 * — see superpowers:dispatching-parallel-agents: "agents would interfere").
 *
 * So the work is split into:
 *   1. A CENTRAL phase (done by the orchestrator, sequentially) that owns every
 *      shared file: the Click flags in cli.py, the shared helpers/envelope in
 *      jsonout/common.py, the test fixtures in conftest.py, and ARCHITECTURE.md.
 *   2. A PARALLEL phase where each agent owns exactly ONE builder module and
 *      ONE test file — disjoint sets, so they never touch the same file.
 *   3. A REVIEW phase (one agent) that runs the suite and reports.
 *
 * This file is a declarative description of that DAG. Run `node
 * .claude/workflows/add-json-flags.js` to print the plan.
 */

const REPO = "."; // run from the worktree / repo root
const PY = "python3";

/** Phase 0 — central scaffold owned by the orchestrator (NOT parallel). */
const central = {
  name: "central-scaffold",
  parallel: false,
  owns: [
    "ARCHITECTURE.md", // JSON contract spec (source of truth: frontend/src/types)
    "aidash/jsonout/common.py", // envelope() + shared formatters/helpers
    "aidash/jsonout/__init__.py", // re-exports builders for cli.py
    "aidash/jsonout/{cost,replay,score,rates,search,exports}.py", // stubs
    "aidash/cli.py", // add --json (5 cmds), --export (cost+score), --weekly (cost)
    "aidash/__main__.py", // enable `python -m aidash` (frontend subprocess entry)
    "pyproject.toml", // pytest dev dep + [tool.pytest.ini_options] testpaths
    "tests/conftest.py", // hermetic synthetic Session fixtures
  ],
  rules: [
    "Each CLI command branches to a builder BEFORE the (untouched) Rich path.",
    "Rich rendering functions are never modified.",
    "Builders return only the `data` dict; cli.py wraps it via common.envelope().",
    "--json prints the envelope; --export/--weekly print raw CSV/JSON/Markdown.",
  ],
};

/**
 * Phase 1 — parallel builder agents. Each agent's `files` are disjoint from
 * every other agent's, which is what makes the parallel dispatch safe.
 */
const builders = [
  {
    agent: "cost",
    builder: "aidash/jsonout/cost.py",
    test: "tests/test_json_cost.py",
    fn: "build_cost_json(sessions, *, period, group_by, agent_filter)",
    spec: "ARCHITECTURE.md §4.1",
    commands: ["cost --json", "cost --by agent --json"],
  },
  {
    agent: "replay",
    builder: "aidash/jsonout/replay.py",
    test: "tests/test_json_replay.py",
    fn: "build_replay_json(sessions, *, target)",
    spec: "ARCHITECTURE.md §4.2",
    commands: ["replay --json", "replay today --json"],
  },
  {
    agent: "score",
    builder: "aidash/jsonout/score.py",
    test: "tests/test_json_score.py",
    fn: "build_score_json(sessions, *, target, trend)",
    spec: "ARCHITECTURE.md §4.3",
    commands: ["score --json", "score --trend --json"],
  },
  {
    agent: "rates",
    builder: "aidash/jsonout/rates.py",
    test: "tests/test_json_rates.py",
    fn: "build_rates_json(sessions, *, period, compare)",
    spec: "ARCHITECTURE.md §4.4",
    commands: ["rates --json", "rates --compare --json"],
  },
  {
    agent: "search",
    builder: "aidash/jsonout/search.py",
    test: "tests/test_json_search.py",
    fn: "build_search_json(sessions, *, query, agent_filter, project, limit)",
    spec: "ARCHITECTURE.md §4.5",
    commands: ["search auth --json"],
  },
  {
    agent: "export",
    builder: "aidash/jsonout/exports.py",
    test: "tests/test_export.py",
    fn: "build_cost_export / build_score_export / build_weekly_markdown",
    spec: "ARCHITECTURE.md §5",
    commands: [
      "cost --export csv",
      "cost --export json",
      "cost --weekly",
      "score --export json",
    ],
  },
];

const builderConstraints = [
  "Touch ONLY your builder file and your test file.",
  "Do NOT edit cli.py, jsonout/common.py, jsonout/__init__.py, conftest.py, or Rich code.",
  "Read ARCHITECTURE.md for the contract; read the matching Rich function for logic.",
  "Tests use CliRunner + the conftest fixtures (runner, sample_sessions, patch_sessions) — hermetic, never read ~/.claude.",
  "Tests must assert: valid JSON, required fields present, types (money=float, tokens=int, displays=str), and the empty case.",
];

/** Phase 2 — single review agent (read-only; reports, does not fix). */
const review = {
  name: "review",
  parallel: false,
  checks: [
    `${PY} -m pytest tests/ -q   # full suite, expect all pass`,
    "confirm no Rich/engine regression (import + --help + git diff scope)",
    "run each command with --json and assert valid envelope + schema fields/types",
    "run exports (csv/json/markdown) and validate",
    "report schema mismatches vs ARCHITECTURE.md and cross-builder inconsistencies",
  ],
  verdict: "GREEN | YELLOW (minor, listed) | RED (blocking)",
};

const workflow = {
  name: "add-json-flags",
  description:
    "Add --json/--export/--weekly to all 5 aidash commands via safe parallel subagents.",
  repo: REPO,
  phases: [
    { phase: 0, ...central },
    {
      phase: 1,
      name: "parallel-builders",
      parallel: true,
      agents: builders,
      constraints: builderConstraints,
    },
    { phase: 2, ...review },
  ],
  verify: [`${PY} -m pytest tests/ -q`, `${PY} -m aidash cost --json`],
};

module.exports = workflow;

if (require.main === module) {
  console.log(JSON.stringify(workflow, null, 2));
}
