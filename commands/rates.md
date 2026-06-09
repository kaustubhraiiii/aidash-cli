---
description: Show per-model pricing from real usage. Flags: --period [weekly|monthly|all] --compare (what-if cross-agent cost)
---

## Pre-flight

```bash
python3 -m aidash --version 2>&1
```

If it fails, stop and tell the user:
> aidash is not installed. Run: `pip install aidash`

## Fetch data

```bash
python3 -m aidash rates --json $ARGUMENTS 2>&1
```

Parse stdout as JSON envelope (`schema_version`, `ok`, `data`, `error`).

## Handle errors

- If `ok` is `false`: show `error.message`. If `error.code` is `bad_argument`, show available flags: `--period [weekly|monthly|all]`, `--compare`.
- If `data.empty` is not null: show `data.empty.suggestion`.

## Render

Never print raw JSON.

**Header line:**
> Rates — period: `{data.period}`

### Per-model table (always shown)

For each row in `data.models[]`:

| Model | Sessions | Input/M | Output/M | Effective/M | Cache hit | Avg/session |
|-------|----------|---------|----------|-------------|-----------|-------------|
| `model` | `session_count` | `input_per_million_display` | `output_per_million_display` | `effective_rate_per_million_display` | `cache_hit_display` | `avg_cost_per_session_display` |

Sort rows as returned (already sorted by model name).

### Comparison table (only when `data.comparison` is not null)

**Header:**
> What if you'd used a different agent?

For each row in `data.comparison.rows[]`:

| Agent | Actual | `{comparator 1}` | `{comparator 2}` | ... | Cheapest |
|-------|--------|-----------------|-----------------|-----|----------|
| `agent_label` (`session_count` sessions) | `actual_cost_display` | `estimates[0].cost_display` | `estimates[1].cost_display` | ... | `cheapest` |

Comparator column headers come from `data.comparison.comparators[]`.

**Footer** (one dim line):
> Flags: `--period weekly|monthly|all` · `--compare` (what-if cost across agents)
