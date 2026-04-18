"""Main CLI entry point with Click group."""

import shutil
from datetime import date, datetime, timedelta

import click
from rich.console import Console
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from aidash.config import MODEL_PRICING, PER_MODEL_PRICING, Pricing, detect_agents
from aidash.loader import PARSER_MAP, load_all_sessions
from aidash.models import Session
from aidash.scoring import ScoreResult, score_session

VERSION = "0.1.0"
BRAND_GREEN = "#5CB85C"

LOGO = (
    " █████  ██ ██████   █████  ███████ ██   ██\n"
    "██   ██ ██ ██   ██ ██   ██ ██      ██   ██\n"
    "███████ ██ ██   ██ ███████ ███████ ███████\n"
    "██   ██ ██ ██   ██ ██   ██      ██ ██   ██\n"
    "██   ██ ██ ██████  ██   ██ ███████ ██   ██"
)

_AGENT_DISPLAY = [
    ("claude_code", "Claude Code", "~/.claude/projects/"),
    ("gemini_cli", "Gemini CLI", "~/.gemini/tmp/"),
    ("codex", "Codex", "~/.codex/sessions/"),
]

_COMMAND_DISPLAY = [
    ("cost", "View spending across all agents"),
    ("replay", "Play back any session as a timeline"),
    ("score", "Rate your efficiency per session"),
    ("rates", "Compare model pricing from real usage"),
    ("search", "Search across all sessions"),
]


def _show_welcome() -> None:
    console = _console()
    console.print(LOGO, style=BRAND_GREEN, markup=False, highlight=False)
    console.print()
    console.print(
        "Track usage, costs, and efficiency across AI coding agents",
        style="dim white",
    )
    console.print(Rule(style=BRAND_GREEN))
    console.print()

    detected = set(detect_agents())
    counts: dict[str, int] = {}
    for agent in detected:
        parser_cls = PARSER_MAP.get(agent)
        if parser_cls is None:
            continue
        try:
            counts[agent] = len(parser_cls().discover_sessions())
        except Exception:
            counts[agent] = 0

    console.print("[bold]Detected Agents[/bold]")
    agents_table = Table(show_header=False, box=None, padding=(0, 2))
    agents_table.add_column(style=BRAND_GREEN, no_wrap=True)
    agents_table.add_column(no_wrap=True)
    agents_table.add_column(justify="right", no_wrap=True)
    for key, label, path in _AGENT_DISPLAY:
        if key in detected:
            agents_table.add_row(
                label,
                f"[dim]{path}[/dim]",
                f"{counts.get(key, 0)} sessions",
            )
        else:
            agents_table.add_row(label, "[dim]not detected[/dim]", "")
    console.print(agents_table)
    console.print()

    console.print("[bold]Commands[/bold]")
    cmd_table = Table(show_header=False, box=None, padding=(0, 2))
    cmd_table.add_column(style=BRAND_GREEN, no_wrap=True)
    cmd_table.add_column()
    for name, desc in _COMMAND_DISPLAY:
        cmd_table.add_row(name, desc)
    console.print(cmd_table)
    console.print()

    console.print(
        "[dim]Run 'aidash <command> --help' for details on any command[/dim]"
    )


def _print_version(ctx: click.Context, param: click.Parameter, value: bool) -> None:
    if not value or ctx.resilient_parsing:
        return
    Console().print(f"aidash v{VERSION}", style=BRAND_GREEN)
    ctx.exit()


def _session_cost(session: Session) -> float:
    """Calculate dollar cost for a session based on its agent's pricing."""
    pricing = MODEL_PRICING.get(session.agent, MODEL_PRICING["claude_code"])
    cost = 0.0
    for msg in session.messages:
        u = msg.token_usage
        if not u:
            continue
        cost += u.input_tokens * pricing.input_per_million / 1_000_000
        cost += u.output_tokens * pricing.output_per_million / 1_000_000
        cost += u.cache_read_input_tokens * pricing.cache_read_per_million / 1_000_000
        cost += u.cache_creation_input_tokens * pricing.cache_write_per_million / 1_000_000
    return cost


def _message_cost(input_tokens: int, output_tokens: int, pricing: Pricing) -> float:
    return (
        input_tokens * pricing.input_per_million / 1_000_000
        + output_tokens * pricing.output_per_million / 1_000_000
    )


def _period_to_since(period: str) -> str | None:
    """Convert a period keyword to a YYYY-MM-DD since date string."""
    today = date.today()
    if period == "today":
        return today.isoformat()
    if period == "weekly":
        return (today - timedelta(days=7)).isoformat()
    if period == "monthly":
        return (today - timedelta(days=30)).isoformat()
    return None  # "all"


def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _console() -> Console:
    """Rich Console with output width capped at 120 cols on wide terminals."""
    width = shutil.get_terminal_size((120, 24)).columns
    return Console(width=min(width, 120))


def _no_sessions_message(
    console: Console,
    *,
    filters: dict[str, str | None] | None = None,
    suggestion: str = "Try removing filters or expanding --period.",
) -> None:
    """Print a friendly diagnostic when filters yield no sessions."""
    detected = detect_agents()

    console.print()
    console.print("[yellow]No sessions matched.[/yellow]")

    if filters:
        active = {
            k: v for k, v in filters.items() if v not in (None, "", "all")
        }
        if active:
            parts = ", ".join(f"{k}={v}" for k, v in active.items())
            console.print(f"  [dim]Active filters: {parts}[/dim]")

    if detected:
        labels = []
        for agent in detected:
            try:
                count = len(PARSER_MAP[agent]().discover_sessions())
            except Exception:
                count = 0
            label = next((l for k, l, _ in _AGENT_DISPLAY if k == agent), agent)
            labels.append(f"{label} ({count})")
        console.print(f"  [dim]Detected agents: {', '.join(labels)}[/dim]")
    else:
        console.print(
            "  [dim]No agents detected. aidash looks for "
            "~/.claude/, ~/.codex/, and ~/.gemini/tmp/[/dim]"
        )

    console.print(f"  [dim]{suggestion}[/dim]")


@click.group(invoke_without_command=True)
@click.option(
    "--version",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=_print_version,
    help="Show version and exit.",
)
@click.pass_context
def cli(ctx: click.Context):
    """aidash — Track and analyze your usage across AI coding agents."""
    if ctx.invoked_subcommand is None:
        _show_welcome()


@cli.command()
@click.option(
    "--period",
    type=click.Choice(["today", "weekly", "monthly", "all"], case_sensitive=False),
    default="all",
    help="Time period to analyze.",
)
@click.option(
    "--by",
    "group_by",
    type=click.Choice(["agent", "project", "model"], case_sensitive=False),
    default=None,
    help="Group results by this field.",
)
@click.option("--agent", default=None, help="Filter to a specific agent.")
def cost(period, group_by, agent):
    """Unified cost dashboard across all agents."""
    console = _console()
    since = _period_to_since(period)
    agents_filter = [agent] if agent else None

    sessions = load_all_sessions(agents=agents_filter, since=since)

    if not sessions:
        _no_sessions_message(
            console,
            filters={"period": period, "agent": agent},
        )
        return

    if group_by:
        _cost_grouped(console, sessions, group_by, period)
    else:
        _cost_detail(console, sessions, period)


def _cost_detail(console: Console, sessions: list[Session], period: str) -> None:
    table = Table(
        title=f"Cost Dashboard — {period}",
        title_style="bold",
        show_lines=False,
    )
    table.add_column("Date", style="cyan", no_wrap=True)
    table.add_column("Agent")
    table.add_column("Project", style="green")
    table.add_column("Model", style="dim")
    table.add_column("Input Tok", justify="right")
    table.add_column("Output Tok", justify="right")
    table.add_column("Cost", justify="right", style="bold yellow")

    total_cost = 0.0
    total_input = 0
    total_output = 0

    for s in sessions:
        c = _session_cost(s)
        total_cost += c
        total_input += s.total_input_tokens
        total_output += s.total_output_tokens

        dt = s.start_time.strftime("%Y-%m-%d %H:%M") if s.start_time else "—"
        table.add_row(
            dt,
            s.agent,
            s.project or "—",
            s.model or "—",
            _fmt_tokens(s.total_input_tokens),
            _fmt_tokens(s.total_output_tokens),
            f"${c:.4f}",
        )

    table.add_section()
    table.add_row(
        f"[bold]{len(sessions)} sessions[/bold]",
        "",
        "",
        "",
        f"[bold]{_fmt_tokens(total_input)}[/bold]",
        f"[bold]{_fmt_tokens(total_output)}[/bold]",
        f"[bold green]${total_cost:.4f}[/bold green]",
    )

    console.print(table)


def _cost_grouped(
    console: Console, sessions: list[Session], group_by: str, period: str
) -> None:
    groups: dict[str, dict] = {}
    for s in sessions:
        key = getattr(s, group_by, "") or "—"
        if key not in groups:
            groups[key] = {"sessions": 0, "tokens": 0, "cost": 0.0}
        groups[key]["sessions"] += 1
        groups[key]["tokens"] += s.total_input_tokens + s.total_output_tokens
        groups[key]["cost"] += _session_cost(s)

    table = Table(
        title=f"Cost by {group_by} — {period}",
        title_style="bold",
    )
    table.add_column(group_by.capitalize(), style="cyan")
    table.add_column("Sessions", justify="right")
    table.add_column("Total Tokens", justify="right")
    table.add_column("Total Cost", justify="right", style="bold yellow")

    total_cost = 0.0
    for key, data in sorted(groups.items(), key=lambda x: x[1]["cost"], reverse=True):
        total_cost += data["cost"]
        table.add_row(
            key,
            str(data["sessions"]),
            _fmt_tokens(data["tokens"]),
            f"${data['cost']:.4f}",
        )

    table.add_section()
    table.add_row(
        f"[bold]Total[/bold]",
        f"[bold]{len(sessions)}[/bold]",
        "",
        f"[bold green]${total_cost:.4f}[/bold green]",
    )

    console.print(table)


@cli.command()
@click.argument("target", default="last")
def replay(target):
    """Play back a coding session as a terminal timeline.

    TARGET can be "last", "today", or a session ID substring.
    """
    console = _console()

    if target == "today":
        sessions = load_all_sessions(since=date.today().isoformat())
        filters = {"target": "today"}
    else:
        sessions = load_all_sessions()
        filters = None

    if not sessions:
        _no_sessions_message(console, filters=filters)
        return

    if target == "last":
        to_replay = [sessions[0]]
    elif target == "today":
        to_replay = sessions
    else:
        to_replay = [s for s in sessions if target in s.id]
        if not to_replay:
            _no_sessions_message(
                console,
                filters={"id_match": target},
                suggestion="Check the session ID (try 'aidash search' to find one).",
            )
            return

    with console.pager(styles=True):
        for session in to_replay:
            _render_session(console, session)
            console.print()


def _render_session(console: Console, session: Session) -> None:
    pricing = MODEL_PRICING.get(session.agent, MODEL_PRICING["claude_code"])
    header = Text()
    header.append(f"━━━ Session: ", style="bold")
    header.append(session.id or "unknown", style="bold cyan")
    header.append(f"  agent={session.agent}", style="dim")
    header.append(f"  project={session.project or '—'}", style="dim")
    if session.start_time:
        header.append(f"  {session.start_time.strftime('%Y-%m-%d %H:%M')}", style="dim")
    header.append(" ━━━", style="bold")
    console.print(header)
    console.print()

    prev_time: datetime | None = None

    for msg in session.messages:
        # Elapsed time since previous message
        if msg.timestamp and prev_time:
            delta = msg.timestamp - prev_time
            secs = int(delta.total_seconds())
            if secs > 0:
                if secs >= 60:
                    elapsed_str = f"+{secs // 60}m{secs % 60:02d}s"
                else:
                    elapsed_str = f"+{secs}s"
                console.print(f"  [dim]{elapsed_str}[/dim]")

        if msg.role == "user":
            console.print(f"[bold cyan]▶ User:[/bold cyan] {msg.content_preview}")
        elif msg.role == "assistant":
            # Tool calls
            for tc in msg.tool_calls:
                console.print(f"  [yellow]🔧 {tc.name}[/yellow]")

            # Text content
            if msg.content_preview:
                console.print(f"  [white]{msg.content_preview}[/white]", end="")
                # Token cost
                if msg.token_usage:
                    c = _message_cost(
                        msg.token_usage.input_tokens,
                        msg.token_usage.output_tokens,
                        pricing,
                    )
                    console.print(f"  [dim](${c:.4f})[/dim]")
                else:
                    console.print()
            elif msg.token_usage:
                c = _message_cost(
                    msg.token_usage.input_tokens,
                    msg.token_usage.output_tokens,
                    pricing,
                )
                console.print(f"  [dim](${c:.4f})[/dim]")

        prev_time = msg.timestamp

    # Session summary
    console.print()
    total = _session_cost(session)
    console.print(
        f"[bold]Total:[/bold] {len(session.messages)} messages, "
        f"{_fmt_tokens(session.total_input_tokens)} in / "
        f"{_fmt_tokens(session.total_output_tokens)} out, "
        f"[bold green]${total:.4f}[/bold green]"
    )


@cli.command()
@click.argument("target", default="last")
@click.option("--trend", is_flag=True, help="Show week-over-week score trend.")
def score(target, trend):
    """Rate your sessions on a 0-100 efficiency scale.

    TARGET can be "last", "today", "all", or a session ID substring.
    """
    console = _console()

    if trend:
        _score_trend(console)
        return

    sessions = load_all_sessions()
    if not sessions:
        _no_sessions_message(console)
        return

    if target == "last":
        to_score = [sessions[0]]
    elif target == "today":
        today_str = date.today().isoformat()
        to_score = load_all_sessions(since=today_str)
        if not to_score:
            _no_sessions_message(console, filters={"target": "today"})
            return
    elif target == "all":
        to_score = sessions
    else:
        to_score = [s for s in sessions if target in s.id]
        if not to_score:
            _no_sessions_message(
                console,
                filters={"id_match": target},
                suggestion="Check the session ID (try 'aidash search' to find one).",
            )
            return

    for s in to_score:
        _render_score(console, s)
        if len(to_score) > 1:
            console.print()


def _score_color(val: float) -> str:
    if val >= 70:
        return "green"
    if val >= 40:
        return "yellow"
    return "red"


def _verdict(total: float) -> str:
    if total >= 70:
        return "Efficient session"
    if total >= 40:
        return "Room for improvement"
    return "Rough session — lots of back and forth"


def _render_score(console: Console, session: Session) -> None:
    result = score_session(session)
    dt = session.start_time.strftime("%Y-%m-%d %H:%M") if session.start_time else "—"

    console.print(
        f"[bold]Session:[/bold] [cyan]{session.id[:8]}[/cyan]  "
        f"[dim]{dt}  {session.agent}  {session.project or '—'}[/dim]"
    )
    console.print()

    table = Table(
        show_header=True,
        box=None,
        padding=(0, 2),
    )
    table.add_column("Metric", style="bold")
    table.add_column("Raw", justify="right")
    table.add_column("Score", justify="right")

    rows = [
        ("Prompt ratio", f"{result.prompt_ratio_raw:.2f}", result.prompt_ratio_score),
        ("Tool efficiency", f"{result.tool_efficiency_raw:.2f}", result.tool_efficiency_score),
        ("Token density", f"{result.token_density_raw:.0f}", result.token_density_score),
        ("Session focus", f"{result.session_focus_raw} tools", result.session_focus_score),
    ]
    for name, raw, sub in rows:
        color = _score_color(sub)
        table.add_row(name, raw, f"[{color}]{sub:.0f}[/{color}]")

    console.print(table)
    console.print()

    color = _score_color(result.total)
    console.print(f"  [bold]Weighted total:[/bold]  [{color} bold]{result.total:.0f}/100[/{color} bold]")
    console.print(f"  [{color}]{_verdict(result.total)}[/{color}]")


def _score_trend(console: Console) -> None:
    sessions = load_all_sessions()
    if not sessions:
        _no_sessions_message(console)
        return

    # Group by ISO week
    weeks: dict[str, list[float]] = {}
    for s in sessions:
        if not s.start_time:
            continue
        iso = s.start_time.isocalendar()
        week_label = f"{iso[0]}-W{iso[1]:02d}"
        result = score_session(s)
        weeks.setdefault(week_label, []).append(result.total)

    # Take last 8 weeks sorted chronologically
    sorted_weeks = sorted(weeks.keys())[-8:]

    if not sorted_weeks:
        _no_sessions_message(
            console,
            suggestion="Sessions exist but none have parseable timestamps for trending.",
        )
        return

    console.print("[bold]Weekly Score Trend[/bold]")
    console.print()

    max_bar = 40  # max bar width in chars

    for week in sorted_weeks:
        scores = weeks[week]
        avg = sum(scores) / len(scores)
        bar_len = int(avg / 100 * max_bar)
        color = _score_color(avg)
        bar = "\u2588" * bar_len
        console.print(
            f"  {week}  [{color}]{bar}[/{color}]  "
            f"[{color} bold]{avg:.0f}[/{color} bold]  "
            f"[dim]({len(scores)} sessions)[/dim]"
        )


@cli.command()
@click.option("--compare", is_flag=True, help="Show what-if cost comparison across agents.")
@click.option(
    "--period",
    type=click.Choice(["weekly", "monthly", "all"], case_sensitive=False),
    default="all",
    help="Time period to analyze.",
)
def rates(compare, period):
    """Compare pricing across models and agents."""
    console = _console()
    since = _period_to_since(period)
    sessions = load_all_sessions(since=since)

    if not sessions:
        _no_sessions_message(console, filters={"period": period})
        return

    _rates_table(console, sessions, period)

    if compare:
        console.print()
        _rates_compare(console, sessions, period)


def _rates_table(console: Console, sessions: list[Session], period: str) -> None:
    """Display per-model rate breakdown computed from real session data."""
    groups: dict[str, list[Session]] = {}
    for s in sessions:
        model = s.model or "unknown"
        groups.setdefault(model, []).append(s)

    table = Table(
        title=f"Rate Breakdown by Model — {period}",
        title_style="bold",
    )
    table.add_column("Model", style="cyan")
    table.add_column("Sessions", justify="right")
    table.add_column("In/1M", justify="right")
    table.add_column("Out/1M", justify="right")
    table.add_column("Avg/Session", justify="right", style="bold yellow")
    table.add_column("I/O Ratio", justify="right")
    table.add_column("Cache Hit%", justify="right", style="green")
    table.add_column("Eff. Rate/1M", justify="right", style="bold magenta")

    for model, model_sessions in sorted(groups.items()):
        pricing = _resolve_model_pricing(model, model_sessions)

        total_cost = 0.0
        total_input = 0
        total_output = 0
        total_cache_read = 0
        total_cache_write = 0

        for s in model_sessions:
            total_cost += _session_cost(s)
            for msg in s.messages:
                u = msg.token_usage
                if not u:
                    continue
                total_input += u.input_tokens
                total_output += u.output_tokens
                total_cache_read += u.cache_read_input_tokens
                total_cache_write += u.cache_creation_input_tokens

        n = len(model_sessions)
        avg_cost = total_cost / n if n else 0.0

        io_total = total_input + total_output
        io_ratio = (total_input / io_total * 100) if io_total > 0 else 0.0

        input_side = total_input + total_cache_read + total_cache_write
        cache_hit = (total_cache_read / input_side * 100) if input_side > 0 else 0.0

        all_tokens = input_side + total_output
        effective = (total_cost / all_tokens * 1_000_000) if all_tokens > 0 else 0.0

        table.add_row(
            model,
            str(n),
            f"${pricing.input_per_million:.2f}",
            f"${pricing.output_per_million:.2f}",
            f"${avg_cost:.4f}",
            f"{io_ratio:.0f}%",
            f"{cache_hit:.1f}%",
            f"${effective:.2f}",
        )

    console.print(table)


def _rates_compare(console: Console, sessions: list[Session], period: str) -> None:
    """What-if comparison: what would agent A's usage cost on agent B's pricing."""
    # Group by agent
    agent_groups: dict[str, dict] = {}
    for s in sessions:
        agent = s.agent
        if agent not in agent_groups:
            agent_groups[agent] = {
                "sessions": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read": 0,
                "cache_write": 0,
                "actual_cost": 0.0,
            }
        g = agent_groups[agent]
        g["sessions"] += 1
        g["actual_cost"] += _session_cost(s)
        for msg in s.messages:
            u = msg.token_usage
            if not u:
                continue
            g["input_tokens"] += u.input_tokens
            g["output_tokens"] += u.output_tokens
            g["cache_read"] += u.cache_read_input_tokens
            g["cache_write"] += u.cache_creation_input_tokens

    comparators = [
        (label, MODEL_PRICING[key])
        for label, key in (
            ("Claude", "claude_code"),
            ("Gemini", "gemini_cli"),
            ("Codex", "codex"),
        )
        if key in MODEL_PRICING
    ]

    table = Table(
        title=f"What-If Cost Comparison — {period}",
        title_style="bold",
    )
    table.add_column("Your Agent", style="cyan")
    table.add_column("Sessions", justify="right")
    table.add_column("Actual Cost", justify="right", style="bold yellow")
    for label, _ in comparators:
        table.add_column(f"If {label}", justify="right")
    table.add_column("Cheapest", justify="right", style="bold green")

    for agent, g in sorted(agent_groups.items()):
        inp = g["input_tokens"]
        out = g["output_tokens"]
        cr = g["cache_read"]
        cw = g["cache_write"]

        estimates: list[tuple[str, float]] = []
        for label, pricing in comparators:
            cost = (
                inp * pricing.input_per_million / 1_000_000
                + out * pricing.output_per_million / 1_000_000
                + cr * pricing.cache_read_per_million / 1_000_000
                + cw * pricing.cache_write_per_million / 1_000_000
            )
            # Agents without caching charge cache tokens at input rate
            if pricing.cache_read_per_million == 0.0:
                cost = (
                    (inp + cr + cw) * pricing.input_per_million / 1_000_000
                    + out * pricing.output_per_million / 1_000_000
                )
            estimates.append((label, cost))

        cheapest = min(estimates, key=lambda x: x[1])[0]

        table.add_row(
            agent,
            str(g["sessions"]),
            f"${g['actual_cost']:.4f}",
            *[f"${c:.4f}" for _, c in estimates],
            cheapest,
        )

    console.print(table)


def _resolve_model_pricing(model: str, sessions: list[Session]) -> Pricing:
    """Look up pricing for a model name, falling back to agent pricing."""
    if model in PER_MODEL_PRICING:
        return PER_MODEL_PRICING[model]
    # Fall back to agent-level pricing from first session
    if sessions:
        return MODEL_PRICING.get(sessions[0].agent, MODEL_PRICING["claude_code"])
    return MODEL_PRICING["claude_code"]


@cli.command()
@click.argument("query")
@click.option("--agent", default=None, help="Filter to a specific agent.")
@click.option("--project", default=None, help="Filter by project name (substring).")
@click.option("--limit", default=10, help="Max results to show.", show_default=True)
def search(query, agent, project, limit):
    """Full-text search across all sessions.

    QUERY is a required search term matched against user messages and tool names.
    """
    console = _console()
    agents_filter = [agent] if agent else None
    sessions = load_all_sessions(agents=agents_filter, project=project)

    query_lower = query.lower()
    scored: list[tuple[int, Session, str]] = []

    for s in sessions:
        blob_parts: list[str] = []
        first_match_preview = ""
        for msg in s.messages:
            if msg.role == "user" and msg.content_preview:
                blob_parts.append(msg.content_preview)
            for tc in msg.tool_calls:
                blob_parts.append(tc.name)
        blob = " ".join(blob_parts).lower()
        count = blob.count(query_lower)
        if count == 0:
            continue
        # Find first matching user message for preview
        for msg in s.messages:
            if msg.role == "user" and msg.content_preview:
                if query_lower in msg.content_preview.lower():
                    first_match_preview = msg.content_preview[:80]
                    break
        if not first_match_preview:
            first_match_preview = blob_parts[0][:80] if blob_parts else ""
        scored.append((count, s, first_match_preview))

    # Sort by hit count desc, then recency desc
    epoch = datetime.min.replace(tzinfo=None)
    scored.sort(key=lambda x: (x[0], x[1].start_time or epoch), reverse=True)
    scored = scored[:limit]

    if not scored:
        _no_sessions_message(
            console,
            filters={"query": query, "agent": agent, "project": project},
            suggestion="Try a broader query or remove --agent/--project filters.",
        )
        return

    table = Table(
        title=f"Search: \"{query}\"",
        title_style="bold",
    )
    table.add_column("#", style="dim", no_wrap=True)
    table.add_column("Date", style="cyan", no_wrap=True)
    table.add_column("Agent")
    table.add_column("Project", style="green")
    table.add_column("Preview")
    table.add_column("Tokens", justify="right")
    table.add_column("Cost", justify="right", style="bold yellow")

    for count, s, preview in scored:
        dt = s.start_time.strftime("%Y-%m-%d %H:%M") if s.start_time else "—"
        total_tok = s.total_input_tokens + s.total_output_tokens
        c = _session_cost(s)

        # Highlight query in preview
        highlighted = _highlight_query(preview, query)

        table.add_row(
            s.id[:8],
            dt,
            s.agent,
            s.project or "—",
            highlighted,
            _fmt_tokens(total_tok),
            f"${c:.4f}",
        )

    console.print(table)
    console.print(
        f"\n[dim]Run 'aidash replay <session-id>' to view full session[/dim]"
    )


def _highlight_query(text: str, query: str) -> Text:
    """Return a Rich Text with all occurrences of query highlighted."""
    result = Text()
    text_lower = text.lower()
    query_lower = query.lower()
    i = 0
    while i < len(text):
        pos = text_lower.find(query_lower, i)
        if pos == -1:
            result.append(text[i:])
            break
        result.append(text[i:pos])
        result.append(text[pos : pos + len(query)], style="bold yellow")
        i = pos + len(query)
    return result
