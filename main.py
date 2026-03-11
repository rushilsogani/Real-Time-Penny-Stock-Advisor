from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stockmarkpred.config import Settings
from stockmarkpred.runner import SignalRunner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the StockMarkPred penny-stock intraday scanner."
    )
    parser.add_argument(
        "--env",
        default=".env",
        help="Path to the environment file that stores Alpaca credentials.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single scan cycle and exit.",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=None,
        help="Run a fixed number of scan cycles before exiting.",
    )
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=None,
        help="Override the scan interval from the environment file.",
    )
    parser.add_argument(
        "--candidate-limit",
        type=int,
        default=None,
        help="Override how many symbols are pulled from the screener each cycle.",
    )
    parser.add_argument(
        "--max-ideas",
        type=int,
        default=None,
        help="Override how many ranked ideas are shown each cycle.",
    )
    parser.add_argument(
        "--symbols",
        nargs="*",
        default=None,
        help="Optional manual symbol override to add to the live screener.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce non-signal console output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        settings = Settings.load(Path(args.env))
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    if args.poll_seconds is not None:
        settings.poll_seconds = max(5, args.poll_seconds)
    if args.candidate_limit is not None:
        settings.candidate_limit = max(5, args.candidate_limit)
    if args.max_ideas is not None:
        settings.max_ideas = max(1, args.max_ideas)
    if args.symbols:
        merged = {symbol.upper() for symbol in settings.watchlist}
        merged.update(symbol.upper() for symbol in args.symbols)
        settings.watchlist = sorted(merged)
    if args.quiet:
        settings.verbose = False

    runner = SignalRunner(settings)
    return runner.run(once=args.once, max_cycles=args.max_cycles)


if __name__ == "__main__":
    raise SystemExit(main())
