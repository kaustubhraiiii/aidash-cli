---
description: Show AI spending breakdown by agent, project, or model. Flags: --period [today|weekly|monthly|all] --by [agent|project|model] --agent <name>
---

## Pre-flight

Run this first:
```bash
python -m aidash --version 2>&1
```

If the command fails (exit code non-zero or "No module named"), stop and tell the user:
> aidash is not installed. Run: `pip install aidash`

## Fetch data

```bash
python -m aidash cost --json $ARGUMENTS 2>&1
```

Parse the stdout as JSON. The envelope shape is:
```json
{ "schema_version": "1.0", "ok": true|false, "data": {...}, "error": {"code": "...", "message": "..."} }
```

## Handle errors

- If `ok` is `false`: show `error.message` as a clear error. If `error.code` is `bad_argument`, show the available flags: `--period [today|weekly|monthly|all]`, `--by [agent|project|model]`, `--agent <name>`.
- If `data.empty` is not null: show `data.empty.suggestion` as a friendly note. List any agents in `data.empty.detected_agents` as "Detected: Claude Code (12 sessions)".

## Render

Never print raw JSON.

**Header line** (one line of prose):
> `{data.totals.session_count}` sessions · `{data.totals.tokens.total_tokens_display}` tokens · **`{data.totals.cost_display}`** — period: `{data.period}`

**7-day alert** (only if today's spend > 7-day mean across the `data.rows` dates):
> ⚠ Today's spend is above the 7-day average

**Main table** — if `data.view` is `"detail"`:

| Date | Agent | Project | Model | Tokens | Cost |
|------|-------|---------|-------|--------|------|
| `date_display` | `agent_label` | `project` (truncate at 20 chars) | `model` (truncate at 22 chars) | `tokens.total_tokens_display` | `cost_display` |

If `data.view` is `"grouped"`:

| Group | Sessions | Tokens | Cost |
|-------|----------|--------|------|
| `key_label` | `session_count` | `tokens.total_tokens_display` | `cost_display` |

**Footer hint** (one dim line):
> Flags: `--period today|weekly|monthly|all` · `--by agent|project|model` · `--agent <name>`
