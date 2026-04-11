"""Main CLI entry point with Click group."""

from datetime import date, datetime, timedelta

import click
from rich.console import Console
from rich.table import Table
from rich.text import Text

from aidash.config import MODEL_PRICING, PER_MODEL_PRICING, Pricing
from aidash.loader import load_all_sessions
from aidash.models import Session
from aidash.scoring import ScoreResult, score_session


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


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """aidash — Track and analyze your usage across AI coding agents."""


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
    console = Console()
    since = _period_to_since(period)
    agents_filter = [agent] if agent else None

    sessions = load_all_sessions(agents=agents_filter, since=since)

    if not sessions:
        console.print("[dim]No sessions found for the given filters.[/dim]")
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
    console = Console()

    if target == "today":
        sessions = load_all_sessions(since=date.today().isoformat())
    else:
        sessions = load_all_sessions()

    if not sessions:
        console.print("[dim]No sessions found.[/dim]")
        return

    if target == "last":
        to_replay = [sessions[0]]
    elif target == "today":
        to_replay = sessions
    else:
        to_replay = [s for s in sessions if target in s.id]
        if not to_replay:
            console.print(f"[red]No session matching '{target}'[/red]")
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
@click.option("--target", default="last", help="'last', 'today', 'all', or session ID substring.")
@click.option("--trend", is_flag=True, help="Show week-over-week score trend.")
def score(target, trend):
    """Rate your sessions on a 0-100 efficiency scale."""
    console = Console()

    if trend:
        _score_trend(console)
        return

    sessions = load_all_sessions()
    if not sessions:
        console.print("[dim]No sessions found.[/dim]")
        return

    if target == "last":
        to_score = [sessions[0]]
    elif target == "today":
        today_str = date.today().isoformat()
        to_score = load_all_sessions(since=today_str)
    elif target == "all":
        to_score = sessions
    else:
        to_score = [s for s in sessions if target in s.id]
        if not to_score:
            console.print(f"[red]No session matching '{target}'[/red]")
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

    table = Table(show_header=True, box=None, padding=(0, 2))
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
        console.print("[dim]No sessions found.[/dim]")
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
        console.print("[dim]No datable sessions found.[/dim]")
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
@click.option(
    "--period",
    type=click.Choice(["weekly", "monthly", "all"], case_sensitive=False),
    default="all",
    help="Time period to analyze.",
)
def rates(period):
    """Compare pricing across models and agents."""
    console = Console()
    since = _period_to_since(period)
    sessions = load_all_sessions(since=since)

    if not sessions:
        console.print("[dim]No sessions found for the given filters.[/dim]")
        return

    _rates_table(console, sessions, period)


def _rates_table(console: Console, sessions: list[Session], period: str) -> None:
    """Display per-model rate breakdown from real session data."""
    # Group sessions by model
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
    table.add_column("List In/1M", justify="right")
    table.add_column("List Out/1M", justify="right")
    table.add_column("Your Avg/Session", justify="right", style="bold yellow")
    table.add_column("Cache Hit%", justify="right", style="green")
    table.add_column("Effective Rate", justify="right", style="bold magenta")

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

        # Input vs output ratio
        all_tokens = total_input + total_cache_read + total_cache_write + total_output
        # Cache hit rate: cache_read / total_input_side tokens
        input_side = total_input + total_cache_read + total_cache_write
        cache_hit = (total_cache_read / input_side * 100) if input_side > 0 else 0.0

        # Effective rate: actual cost / total_tokens * 1M (blended per-million)
        effective = (total_cost / all_tokens * 1_000_000) if all_tokens > 0 else 0.0

        table.add_row(
            model,
            str(n),
            f"${pricing.input_per_million:.2f}",
            f"${pricing.output_per_million:.2f}",
            f"${avg_cost:.4f}",
            f"{cache_hit:.1f}%",
            f"${effective:.2f}/1M",
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
    console = Console()
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
        console.print(f"[dim]No sessions matching '{query}'.[/dim]")
        return

    table = Table(title=f"Search: \"{query}\"", title_style="bold")
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
