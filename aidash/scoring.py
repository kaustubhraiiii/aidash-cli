"""Session efficiency scoring."""

from dataclasses import dataclass

from aidash.models import Session


@dataclass
class ScoreResult:
    prompt_ratio_raw: float
    prompt_ratio_score: float
    tool_efficiency_raw: float
    tool_efficiency_score: float
    token_density_raw: float
    token_density_score: float
    session_focus_raw: int
    session_focus_score: float
    total: float


def _linear(value: float, best: float, worst: float) -> float:
    """Linearly interpolate a score between 0 and 100.

    Returns 100 when value is at or beyond `best`, 0 at or beyond `worst`.
    """
    if best <= worst:
        clamped = max(best, min(value, worst))
        return 100.0 * (1.0 - (clamped - best) / (worst - best))
    else:
        clamped = max(worst, min(value, best))
        return 100.0 * (clamped - worst) / (best - worst)


def score_session(session: Session) -> ScoreResult:
    """Score a session on a 0-100 efficiency scale."""
    user_msgs = sum(1 for m in session.messages if m.role == "user")
    asst_msgs = sum(1 for m in session.messages if m.role == "assistant")

    # 1. Prompt-to-completion ratio (30%)
    if asst_msgs > 0:
        prompt_ratio = user_msgs / asst_msgs
    else:
        prompt_ratio = float(user_msgs) if user_msgs else 1.0
    prompt_score = _linear(prompt_ratio, best=0.33, worst=2.0)

    # 2. Tool call efficiency (25%)
    all_tool_names: list[str] = []
    for m in session.messages:
        for tc in m.tool_calls:
            all_tool_names.append(tc.name)
    total_calls = len(all_tool_names)
    unique_calls = len(set(all_tool_names))
    if total_calls > 0:
        tool_ratio = unique_calls / total_calls
    else:
        tool_ratio = 1.0  # no tools = no thrashing
    tool_score = _linear(tool_ratio, best=0.5, worst=0.1)

    # 3. Token density (25%)
    if asst_msgs > 0:
        token_density = session.total_output_tokens / asst_msgs
    else:
        token_density = 0.0
    density_score = _linear(token_density, best=1000.0, worst=100.0)

    # 4. Session focus (20%)
    distinct_tools = len(set(all_tool_names))
    if 3 <= distinct_tools <= 8:
        focus_score = 100.0
    elif distinct_tools <= 2:
        focus_score = 50.0
    elif distinct_tools <= 15:
        focus_score = 50.0
    else:
        focus_score = 25.0

    total = (
        prompt_score * 0.30
        + tool_score * 0.25
        + density_score * 0.25
        + focus_score * 0.20
    )

    return ScoreResult(
        prompt_ratio_raw=prompt_ratio,
        prompt_ratio_score=prompt_score,
        tool_efficiency_raw=tool_ratio,
        tool_efficiency_score=tool_score,
        token_density_raw=token_density,
        token_density_score=density_score,
        session_focus_raw=distinct_tools,
        session_focus_score=focus_score,
        total=total,
    )
