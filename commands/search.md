---
description: Search sessions by keyword. Args: <query> [--agent <name>] [--project <name>] [--limit <n>]
---

## Pre-flight

```bash
python -m aidash --version 2>&1
```

If it fails, stop and tell the user:
> aidash is not installed. Run: `pip install aidash`

## Fetch data

```bash
python -m aidash search --json $ARGUMENTS 2>&1
```

`$ARGUMENTS` must start with the search query (e.g. `auth --agent claude_code`). The query is required — if `$ARGUMENTS` is empty, tell the user: "Provide a search query: `/aidash:search <query>`"

Parse stdout as JSON envelope (`schema_version`, `ok`, `data`, `error`).

## Handle errors

- If `ok` is `false`: show `error.message`. If `error.code` is `bad_argument` and the query is missing, say: "A query is required. Usage: `/aidash:search <query> [--agent <name>] [--project <name>] [--limit <n>]`"
- If `data.empty` is not null: show `data.empty.suggestion`. E.g. "No sessions matched 'auth'. Try a broader query or remove filters."

## Render

Never print raw JSON.

**Header line:**
> `{data.result_count}` result(s) for **"`{data.query}`"** (showing up to `{data.limit}`)

**Results list** — for each row in `data.rows[]`:

```
{rank}. [{agent_label}] {project} — {date_display} · {tokens.total_tokens_display} tokens · {cost_display}
   {highlighted_preview}
   {session_id_short}
```

Where `highlighted_preview` is built from `row.preview_segments[]`: join all segment texts, wrapping segments where `match` is `true` in **bold** (e.g. `**auth**`). If `preview_segments` is empty, use `row.preview` as plain text.

Separate results with a blank line.

**Footer** (one dim line):
> Flags: `--agent <name>` · `--project <name>` · `--limit <n>` (default 10)
