from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from stockmarkpred.models import TradeIdea

EASTERN = ZoneInfo("America/New_York")


def _fmt_price(value: float) -> str:
    return f"{value:.4f}" if value < 10 else f"{value:.2f}"


def render_dashboard(ideas: list[TradeIdea], scanned_count: int, cycle_time: datetime) -> str:
    cycle_label = cycle_time.astimezone(EASTERN).strftime("%Y-%m-%d %I:%M:%S %p ET")
    lines = [
        "=" * 122,
        f"StockMarkPred live scan | {cycle_label} | scanned {scanned_count} penny-stock candidates",
        "-" * 122,
    ]

    if not ideas:
        lines.append("No symbols cleared the current thresholds.")
        lines.append("=" * 122)
        return "\n".join(lines)

    header = (
        f"{'SYM':<7}{'ACT':<7}{'SCORE':<8}{'LAST':<12}{'ENTRY':<12}"
        f"{'STOP':<12}{'TARGET':<12}{'RVOL':<8}{'GAP%':<8}{'AS OF':<32}"
    )
    lines.append(header)
    lines.append("-" * 122)

    for idea in ideas:
        as_of_label = idea.as_of.astimezone(EASTERN).strftime("%Y-%m-%d %I:%M %p ET")
        lines.append(
            f"{idea.symbol:<7}{idea.action:<7}{idea.score:<8}{_fmt_price(idea.current_price):<12}"
            f"{_fmt_price(idea.entry_price):<12}{_fmt_price(idea.stop_loss):<12}"
            f"{_fmt_price(idea.take_profit):<12}{idea.relative_volume:<8.2f}"
            f"{idea.gap_pct:<8.2f}{as_of_label:<32}"
        )
        lines.append(f"  why: {'; '.join(idea.reasons)}")
    lines.append("=" * 122)
    return "\n".join(lines)


def append_signal_log(path: Path, ideas: list[TradeIdea]) -> None:
    if not ideas:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for idea in ideas:
            handle.write(json.dumps(idea.to_dict(), sort_keys=True))
            handle.write("\n")
