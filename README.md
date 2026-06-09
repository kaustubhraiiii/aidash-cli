<p align="center"><img src="aidash/assets/logo.svg" alt="aidash" width="400"></p>

<p align="center"><em>Track usage, costs, and efficiency across AI coding agents.</em></p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-3776AB?logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/node-18+-339933?logo=node.js&logoColor=white" alt="Node 18+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License: MIT">
  <img src="https://img.shields.io/badge/version-0.2.0-blue" alt="Version 0.2.0">
</p>

---

## Supported Agents

| Agent        | Log Location                    | Status    |
|--------------|---------------------------------|-----------|
| Claude Code  | `~/.claude/projects/`           | Supported |
| Gemini CLI   | `~/.gemini/tmp/<hash>/chats/`   | Supported |
| OpenAI Codex | `~/.codex/sessions/`            | Supported |

aidash auto-detects which agents are installed. No API keys, no config.

## Installation

**Python engine** (required):
```bash
pip install aidash
```

**Ink terminal UI** (optional, for interactive views):
```bash
npm install -g aidash-ui
```

### Development

```bash
git clone https://github.com/kaustubhraiiii/aidash.git
cd aidash
pip install -e .
cd frontend && npm install && npm run build
```

## Quick Start

**CLI (Python engine):**
```bash
aidash                          # show available commands
aidash cost --period weekly     # last 7 days of spend
aidash score last               # rate your most recent session
aidash search "auth"            # full-text search across sessions
```

**Ink interactive views** (requires `aidash-ui`):
```bash
aidash-ui cost                  # interactive cost dashboard
aidash-ui replay last           # scrollable session timeline
aidash-ui score --trend         # efficiency score with trend
aidash-ui rates --compare       # model pricing comparison
aidash-ui search "auth"         # live search results
```

**JSON output** (pipe-friendly, same data as views):
```bash
aidash-ui cost --json           # structured JSON envelope
aidash-ui search "auth" --json  # use in scripts
```

## Commands

### `cost`
Unified cost dashboard across all agents.

```bash
aidash cost
aidash cost --period monthly --by agent
aidash cost --agent claude_code
aidash cost --export csv        # export to file
```

### `replay`
Play back a coding session as a scrollable terminal timeline.

```bash
aidash replay last
aidash replay today
aidash replay a1b2c3d4
```

### `score`
Rate your sessions on a 0-100 efficiency scale.

```bash
aidash score last
aidash score --trend
aidash score today
```

### `rates`
Compare pricing across models and agents.

```bash
aidash rates
aidash rates --compare
aidash rates --period monthly
```

### `search`
Full-text search across all sessions.

```bash
aidash search "auth migration"
aidash search --agent claude_code "database"
aidash search --project myapp "OAuth"
```

## Claude Code Plugin

Install the aidash slash commands directly into Claude Code:

```bash
claude /plugin marketplace add kaustubhraiiii/aidash-cli
```

This adds five slash commands to your Claude Code sessions:

| Command | Description |
|---------|-------------|
| `/aidash:cost` | Cost breakdown with optional period/agent/project filters |
| `/aidash:replay` | Session timeline playback |
| `/aidash:score` | Efficiency score with trend analysis |
| `/aidash:rates` | Per-model pricing from real usage |
| `/aidash:search` | Full-text session search |

**Requires** `pip install aidash` with Python 3 on PATH.

## Scoring Methodology

| Metric                      | Weight | What it measures                                          |
|-----------------------------|:------:|-----------------------------------------------------------|
| Prompt-to-completion ratio  | 30%    | Clarity of instructions — fewer prompts per agent reply.  |
| Tool call efficiency        | 25%    | Diverse, purposeful tool use vs. repetitive thrashing.    |
| Token density               | 25%    | Average meaningful output per agent turn.                 |
| Session focus               | 20%    | Sweet spot of 3–8 distinct tools per session.             |

## How It Works

- **Detection** — Scans for `~/.claude/`, `~/.gemini/tmp/`, and `~/.codex/`.
- **Parsing** — Reads JSONL/JSON session files for messages, tokens, tool calls, timestamps.
- **Normalization** — Maps each agent's format into a common model (Session, Message, TokenUsage, ToolCall).
- **Analysis** — Computes costs, efficiency scores, and what-if comparisons. Strictly read-only.

## Tech Stack

- **Python** 3.10+ — data engine, session parsing, cost calculation
- **[Click](https://click.palletsprojects.com/)** 8.0+ — CLI framework
- **TypeScript** / Node 18+ — Ink frontend
- **[Ink](https://github.com/vadimdemedes/ink)** — React-based terminal UI
- **[termcn](https://github.com/nicholasgasior/termcn)** — terminal component library

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Commit your changes (`git commit -am 'Add my feature'`)
4. Push the branch (`git push origin feat/my-feature`)
5. Open a Pull Request

Bugs and feature requests welcome via [Issues](https://github.com/kaustubhraiiii/aidash/issues).

## License

[MIT](LICENSE) © 2026 Kaustubh Rai
