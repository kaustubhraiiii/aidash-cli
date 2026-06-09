# aidash JSON Contract (ARCHITECTURE.md)

The Ink/TypeScript frontend spawns the Python engine as a subprocess
(`python -m aidash <command> --json`), reads stdout, and renders the result.
This document is the **single source of truth** for that JSON contract. The
TypeScript interfaces in `frontend/src/types/*.ts` mirror it exactly.

`schema_version` is **"1.0"**.

---

## 1. Envelope

Every `--json` invocation prints exactly one JSON object to stdout and exits 0
(empty results are a normal success, not an error):

```jsonc
{
  "schema_version": "1.0",
  "command": "cost",            // cost | replay | score | rates | search
  "ok": true,
  "data": { /* per-command payload, or null on ok:false */ },
  "error": null,                // { "code", "message" } when ok:false
  "meta": {
    "generated_at": "2026-06-06T12:00:00+00:00",  // ISO 8601
    "aidash_version": "0.2.0",
    "period": "weekly",         // echoed period, or null
    "filters": { "agent": "claude_code", "by": null }  // echoed args, string|null
  }
}
```

`error.code` ∈ `bad_argument | session_not_found | parse_error | internal`.

**You do not build the envelope.** `aidash/cli.py` already wraps your `data`
payload via `aidash.jsonout.common.envelope(...)`. Your builder returns only the
`data` dict.

---

## 2. Naming rules (consistency is mandatory)

| Concept | Raw field | Display field | Display format | Helper |
|---|---|---|---|---|
| Money | `*_usd` (float) | `*_display` (str) | `"$0.1234"` cost, `"$3.00"` rates | `fmt_money(v, decimals)` |
| Tokens | `*_tokens` (int) | `*_tokens_display` (str) | `"1.5M"`, `"12.0K"` | `fmt_tokens(n)` |
| Percent | `*_pct` (float 0–100) | `*_display` (str) | `"60%"` | `fmt_pct(v, decimals)` |
| Timestamp | `*_at` (ISO str\|null) | `*_at_display` (str) | `"2026-05-18 09:30"` | `iso_or_none`, `fmt_datetime` |
| Date | `date` (ISO str\|null) | `date_display` (str) | `"2026-05-18"` | `iso_or_none`, `fmt_date` |
| Session id | `session_id` (str) | `session_id_short` (str, 8 ch) | — | `short_id(id)` |
| Agent | `agent` (key str) | `agent_label` (str) | `"Claude Code"` | `agent_label(a)` |
| Rating | `rating` (str) | — | `good`≥70 / `ok`≥40 / `poor` | `rating(v)` |

**Money fields are floats, never strings.** `cost_usd: 0.1234` and
`cost_display: "$0.1234"` both appear. Tokens are ints. Percentages are floats.

---

## 3. Shared building blocks (from `aidash.jsonout.common`)

Import everything you need from `aidash.jsonout import common` (or
`from aidash.jsonout.common import ...`). **Do not edit `common.py`** — it is
shared. Available helpers:

- `fmt_tokens(n) -> str`, `fmt_money(v, decimals=4) -> str`, `fmt_pct(v, decimals=0) -> str`
- `iso_or_none(dt)`, `fmt_datetime(dt)`, `fmt_date(dt)`, `short_id(id)`, `agent_label(a)`, `rating(v)`
- `build_tokens(inp, out, cache_read, cache_creation) -> dict` — the Tokens block
- `build_session_tokens(session) -> dict` — Tokens block for one session
- `build_tokens_for_sessions(sessions) -> dict` — aggregated Tokens block
- `session_cost(session) -> float`, `message_cost(inp, out, pricing) -> float`
- `pricing_for_agent(agent)`, `resolve_model_pricing(model, sessions)`
- `build_empty_state(active_filters: dict, suggestion: str) -> dict`

### Tokens (returned by `build_tokens` / `build_session_tokens`)

```jsonc
{
  "input_tokens": 1500000, "input_tokens_display": "1.5M",
  "output_tokens": 42000, "output_tokens_display": "42.0K",
  "cache_read_tokens": 800000, "cache_read_tokens_display": "800.0K",
  "cache_creation_tokens": 120000, "cache_creation_tokens_display": "120.0K",
  "total_tokens": 2462000, "total_tokens_display": "2.5M"   // sum of all four
}
```

### EmptyState (set on `data.empty` when no rows; otherwise `null`)

```jsonc
{
  "active_filters": { "agent": "codex" },
  "detected_agents": [ { "agent": "claude_code", "agent_label": "Claude Code", "sessions": 12 } ],
  "suggestion": "Try removing filters or expanding --period."
}
```

### ExportBlock (only used inside CSV/JSON export builders, not envelopes)

Export and weekly modes print a **raw string** to stdout (not an envelope).

---

## 4. Per-command `data` payloads

Builders live in `aidash/jsonout/<command>.py`. Each returns the `data` dict
described below. When there are no rows, set the list empty and populate
`empty` via `build_empty_state(...)`; otherwise `empty` is `null`.

### 4.1 `cost` → `build_cost_json(sessions, *, period, group_by, agent_filter)`

```jsonc
{
  "view": "detail",            // "grouped" when group_by is set
  "period": "weekly",
  "group_by": null,            // "agent" | "project" | "model" | null
  "rows": [ /* CostRow or CostGroupRow */ ],
  "totals": { "session_count": 3, "tokens": { /* Tokens */ }, "cost_usd": 0.1234, "cost_display": "$0.1234" },
  "empty": null,
  "export": null,              // always null here; export is a separate mode
  "markdown": null             // always null here; --weekly is a separate mode
}
```

`CostRow` (view "detail"): `session_id`, `session_id_short`, `date`,
`date_display`, `agent`, `agent_label`, `project`, `model`, `tokens` (Tokens),
`cost_usd`, `cost_display`.

`CostGroupRow` (view "grouped", keyed by `group_by`): `key`, `key_label`,
`session_count`, `tokens` (Tokens), `cost_usd`, `cost_display`. Sort by
`cost_usd` descending (matches the Rich table).

### 4.2 `replay` → `build_replay_json(sessions, *, target)`

`sessions` is already period-scoped by the CLI. Select within it:
`last` → first session; `today` → all of them; otherwise → sessions whose `id`
contains `target`. If none match, `sessions: []` + `empty`.

```jsonc
{
  "target": "last",
  "sessions": [ /* ReplaySession */ ],
  "empty": null
}
```

`ReplaySession`: `session_id`, `session_id_short`, `agent`, `agent_label`,
`project`, `model`, `started_at`, `started_at_display`, `ended_at`,
`ended_at_display`, `tokens` (Tokens), `cost_usd`, `cost_display`,
`message_count`, `messages` (ReplayMessage[]).

`ReplayMessage`: `index` (int), `role` ("user"|"assistant"), `content_preview`,
`timestamp`, `timestamp_display`, `elapsed_since_prev_seconds` (int|null),
`elapsed_display` (e.g. `"+1m30s"`, or `""`), `tool_calls`
(`[{ "name", "timestamp" }]`), `tokens` (Tokens|null), `cost_usd`,
`cost_display` (per-message cost via `message_cost`).

### 4.3 `score` → `build_score_json(sessions, *, target, trend)`

```jsonc
// trend = false
{ "view": "sessions", "target": "last", "sessions": [ /* ScoredSession */ ], "weeks": [], "empty": null }
// trend = true
{ "view": "trend", "target": "last", "sessions": [], "weeks": [ /* TrendWeek */ ], "empty": null }
```

Use `aidash.scoring.score_session(session) -> ScoreResult`. Target selection
mirrors the Rich command: `last` → first; `today` → today's sessions; `all` →
all; else id substring.

`ScoredSession`: `session_id`, `session_id_short`, `date`, `date_display`,
`agent`, `agent_label`, `project`, `metrics` (ScoreMetric[]), `total_score`
(float 0–100), `total_display` (e.g. `"82/100"`), `verdict` (str), `rating`.

`ScoreMetric` (one per ScoreResult component — prompt_ratio, tool_efficiency,
token_density, session_focus): `key`, `label`, `raw` (float), `raw_display`
(str), `score` (float 0–100), `score_display` (str), `weight` (float; 0.30,
0.25, 0.25, 0.20), `rating`.

`TrendWeek`: `week` (e.g. `"2026-W21"`), `avg_score` (float), `avg_display`
(str), `session_count` (int), `rating`, `bar_ratio` (float 0–1 = avg/100, for
the frontend to draw a bar). Last 8 weeks, chronological.

### 4.4 `rates` → `build_rates_json(sessions, *, period, compare)`

```jsonc
{
  "period": "all",
  "models": [ /* RateRow */ ],
  "comparison": null,          // RateComparison when compare = true
  "empty": null
}
```

`RateRow` (group sessions by `model`, sort by model name): `model`,
`session_count`, `input_per_million_usd` + `input_per_million_display` (2-dp,
e.g. `"$3.00"`), `output_per_million_usd` + `output_per_million_display`,
`avg_cost_per_session_usd` + `avg_cost_per_session_display` (4-dp),
`io_ratio_pct` + `io_ratio_display` (0-dp `"60%"`), `cache_hit_pct` +
`cache_hit_display` (1-dp `"12.3%"`), `effective_rate_per_million_usd` +
`effective_rate_per_million_display` (2-dp). Pricing via
`resolve_model_pricing(model, model_sessions)`. The formulas match
`_rates_table` in `cli.py`.

`RateComparison`: `comparators` (e.g. `["Claude","Gemini","Codex"]`), `rows`
(RateComparisonRow[]). `RateComparisonRow`: `agent`, `agent_label`,
`session_count`, `actual_cost_usd` + `actual_cost_display`, `estimates`
(`[{ "comparator", "cost_usd", "cost_display" }]`), `cheapest` (comparator
label). Logic mirrors `_rates_compare`.

### 4.5 `search` → `build_search_json(sessions, *, query, agent_filter, project, limit)`

```jsonc
{
  "query": "auth",
  "rows": [ /* SearchRow */ ],
  "result_count": 2,
  "limit": 10,
  "empty": null
}
```

Match logic mirrors the Rich `search`: count occurrences of `query`
(case-insensitive) across user message previews and tool names; skip
zero-match sessions; sort by match count desc, then recency desc; cap at
`limit`.

`SearchRow`: `rank` (1-based int), `session_id`, `session_id_short`, `date`,
`date_display`, `agent`, `agent_label`, `project`, `match_count` (int),
`preview` (str), `preview_segments` (`[{ "text": str, "match": bool }]` — split
the preview so the frontend can highlight matches without re-parsing),
`tokens` (Tokens), `cost_usd`, `cost_display`.

---

## 5. Export & weekly modes (raw stdout, not envelopes)

Builders in `aidash/jsonout/exports.py`. Each returns a **plain string** that
the CLI prints directly:

- `build_cost_export(sessions, *, fmt, period, group_by) -> str` — `fmt="csv"`
  returns CSV (header row + one row per session: date, agent, project, model,
  input_tokens, output_tokens, cost_usd); `fmt="json"` returns
  `json.dumps(...)` of the same rows as a list of flat dicts.
- `build_score_export(sessions, *, fmt, target, trend) -> str` — CSV/JSON of
  per-session scores (session_id, date, agent, project, total_score, and the
  four metric scores).
- `build_weekly_markdown(sessions, *, period) -> str` — a Markdown summary:
  a title, a table of week → sessions → tokens → cost, and a total line.

CSV must be valid (use the `csv` module with a `StringIO`). JSON exports must be
valid JSON. Cost fields stay numeric (float) in JSON exports.

---

## 6. Testing (hermetic, via `tests/conftest.py`)

Each builder ships a test file `tests/test_json_<command>.py` (export tests in
`tests/test_export.py`). Tests invoke through Click's `CliRunner` and patch the
loader using the shared fixtures — **never read real logs**:

```python
import json
from aidash.cli import cli

def test_cost_json_is_valid_and_typed(runner, sample_sessions, patch_sessions):
    patch_sessions(sample_sessions)
    result = runner.invoke(cli, ["cost", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)              # valid JSON
    assert payload["schema_version"] == "1.0"
    assert payload["ok"] is True
    data = payload["data"]
    row = data["rows"][0]
    assert isinstance(row["cost_usd"], float)        # money is float, not str
    assert isinstance(row["cost_display"], str)
    assert isinstance(row["tokens"]["input_tokens"], int)

def test_cost_json_empty(runner, patch_sessions):
    patch_sessions([])
    result = runner.invoke(cli, ["cost", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)["data"]
    assert data["rows"] == []
    assert data["empty"]["suggestion"]
```

Available fixtures: `runner` (CliRunner), `sample_sessions` (3 synthetic
sessions across claude_code / codex / gemini_cli, two ISO weeks, cache + tools),
`patch_sessions(sessions)` (patches `aidash.cli.load_all_sessions`).

Each test file must assert: (1) output parses as JSON, (2) all required schema
fields are present, (3) types match (money = float, tokens = int, displays =
str, ratings ∈ {good, ok, poor}), and (4) the empty case.

---

## 7. Hard constraints for builder agents

- Touch **only** your `aidash/jsonout/<file>.py` and your `tests/test_*.py`.
- Do **not** edit `aidash/cli.py`, `aidash/jsonout/common.py`,
  `aidash/jsonout/__init__.py`, `tests/conftest.py`, or any Rich rendering code.
- Do **not** change existing Rich output. The flags and branches are already
  wired; you only fill in the builder body and write tests.
