---
description: Rate session efficiency 0-100. Args: [last|today|all|<session-id>] [--trend]
---

## Pre-flight

```bash
python3 -m aidash --version 2>&1
```

If it fails, stop and tell the user:
> aidash is not installed. Run: `pip install aidash`

## Fetch data

```bash
python3 -m aidash score --json $ARGUMENTS 2>&1
```

Parse stdout as JSON envelope (`schema_version`, `ok`, `data`, `error`).

## Handle errors

- If `ok` is `false`: show `error.message`. If `error.code` is `session_not_found`, suggest: "Try `last`, `today`, `all`, or a session ID fragment."
- If `data.empty` is not null: show `data.empty.suggestion`.

## Render

Never print raw JSON.

### Trend view (`data.view == "trend"`)

**Header:**
> Score trend — last 8 weeks

**Trend table:**

| Week | Avg Score | Sessions | Bar |
|------|-----------|----------|-----|
| `week` | `avg_display` | `session_count` | `█` × `round(bar_ratio * 20)` chars (color by rating: good=green, ok=yellow, poor=red) |

### Session view (`data.view == "sessions"`)

For each session in `data.sessions[]`:

**Score headline** (large, prominent):
> # `total_display`  (`verdict`)

Rating color: `good` (≥70) → show in green; `ok` (≥40) → yellow; `poor` → red. Use bold/emoji if color is not available: ✅ good, ⚠️ ok, ❌ poor.

**Metrics table:**

| Metric | Score | Raw | Weight |
|--------|-------|-----|--------|
| `label` | `score_display` (`rating`) | `raw_display` | `weight × 100`% |

Rows: prompt_ratio, tool_efficiency, token_density, session_focus.

**Session info** (one dim line):
> `agent_label` · `project` · `date_display` · `tokens.total_tokens_display` tokens

Separate multiple sessions with `---`.

**Footer** (one dim line):
> Args: `last` · `today` · `all` · `<id-fragment>` · `--trend` (week-over-week view)
