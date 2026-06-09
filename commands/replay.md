---
description: Play back a coding session as a prose timeline. Args: [last|today|<session-id>]
---

## Pre-flight

```bash
python3 -m aidash --version 2>&1
```

If it fails, stop and tell the user:
> aidash is not installed. Run: `pip install aidash`

## Fetch data

```bash
python3 -m aidash replay --json $ARGUMENTS 2>&1
```

Parse stdout as JSON envelope (`schema_version`, `ok`, `data`, `error`).

## Handle errors

- If `ok` is `false`: show `error.message`. If `error.code` is `session_not_found`, say "No session matched. Try: `last`, `today`, or a session ID fragment."
- If `data.empty` is not null: show `data.empty.suggestion`.

## Render

Never print raw JSON. Render each session in `data.sessions[]` as a prose timeline.

**Session header** (one line per session):
> **`agent_label`** · `project` · `model` · started `started_at_display` · `message_count` messages · `tokens.total_tokens_display` tokens · `cost_display`

**Message timeline** — for each message in `session.messages[]`:

Format each as a short paragraph:

```
[{index+1}] {timestamp_display}{elapsed} — {ROLE}
{content_preview}
```

Where:
- `ROLE` is **User** or **Claude** (capitalised)
- `{elapsed}` is ` (+{elapsed_display})` if `elapsed_display` is non-empty, otherwise omit
- `content_preview` is the message preview text (show as-is, no truncation)
- If the message has `tool_calls`, append a dim line: `  → tools: {comma-joined tool names}`

Separate messages with a blank line. Use a horizontal rule (`---`) between sessions when multiple sessions are shown.

**Footer** (one dim line at the end):
> Args: `last` (most recent) · `today` (all today's sessions) · `<id-fragment>` (match by session ID)
