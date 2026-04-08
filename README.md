# aidash

A CLI tool that tracks and analyzes your usage across AI coding agents — Claude Code, Gemini CLI, and OpenAI Codex — from a single command line.

## Why aidash?

If you use AI coding agents daily, your session data is scattered across different log directories in different formats. aidash reads all of it, normalizes it, and gives you a unified view of your usage patterns, costs, and efficiency — without any configuration.

## Supported Agents

| Agent | Log Location | Format |
|-------|-------------|--------|
| Claude Code | `~/.claude/projects/` | JSONL (one file per session) |
| Gemini CLI | `~/.gemini/tmp/<hash>/chats/` | JSON/JSONL (per project hash) |
| OpenAI Codex | `~/.codex/sessions/` or `~/.codex/history.jsonl` | JSONL |

aidash auto-detects which agents are installed on your machine. No API keys, no config files, no setup.

## Installation

```bash
git clone https://github.com/yourusername/aidash.git
cd aidash
pip install -e .
```

Requires Python 3.10+.

## Commands

### `aidash cost` — Unified Cost Dashboard

See what you're spending across all agents, broken down by agent, project, or model.

```bash
aidash cost                          # all-time costs
aidash cost --period weekly          # last 7 days
aidash cost --period monthly --by agent   # monthly, grouped by agent
aidash cost --agent claude_code      # filter to one agent
```

### `aidash replay` — Session Replay

Play back any coding session as a scrollable terminal timeline — prompts, tool calls, file edits, token costs, and timing.

```bash
aidash replay last                   # most recent session
aidash replay today                  # all of today's sessions
aidash replay a1b2c3d4              # session by ID prefix
```

### `aidash score` — Efficiency Score

Rates your sessions on a 0-100 scale based on how effectively you worked with the agent. Tracks improvement over time.

```bash
aidash score last                    # score your last session
aidash score --trend                 # weekly trend over last 8 weeks
aidash score today                   # score all of today's sessions
```

**Scoring methodology:**

- **Prompt-to-completion ratio (30%)** — Fewer prompts relative to agent output means clearer instructions. Ideal: 1 prompt per 3+ agent responses.
- **Tool call efficiency (25%)** — High repetition of the same tool suggests thrashing. Diverse, purposeful tool use scores higher.
- **Token density (25%)** — Higher average output per agent response means the agent is doing more meaningful work per turn.
- **Session focus (20%)** — Using 3-8 distinct tools indicates focused, productive work. Too few or too many suggests unfocused sessions.

### `aidash rates` — Rate Comparison

See what you're actually paying per model based on your real usage patterns, not just list prices. Compare what your sessions would cost on different agents.

```bash
aidash rates                         # pricing breakdown by model
aidash rates --compare               # what-if cost comparison across agents
aidash rates --period monthly        # scoped to last 30 days
```

### `aidash search` — Session Search

Full-text search across all your sessions from all agents.

```bash
aidash search "auth migration"                        # search everything
aidash search --agent claude_code "database"           # filter by agent
aidash search --project myapp "OAuth"                  # filter by project
```

## How It Works

aidash is a read-only tool. It discovers and parses the local log files that each AI coding agent already writes to disk:

1. **Detection** — Checks for `~/.claude/`, `~/.gemini/tmp/`, and `~/.codex/` directories
2. **Parsing** — Reads JSONL/JSON session files, extracts messages, token counts, tool calls, and timestamps
3. **Normalization** — Maps each agent's format into a common data model (Session, Message, TokenUsage, ToolCall)
4. **Analysis** — Calculates costs, efficiency scores, and comparisons using the normalized data

**aidash never modifies, deletes, or writes to any log files.** It is strictly read-only.

## Tech Stack

- Python 3.10+
- [Click](https://click.palletsprojects.com/) — CLI framework
- [Rich](https://rich.readthedocs.io/) — Terminal formatting and tables

## License

MIT
