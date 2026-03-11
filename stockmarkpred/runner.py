from __future__ import annotations

import sys
import time
from datetime import UTC, datetime

from stockmarkpred.config import Settings
from stockmarkpred.data import AlpacaDataClient, DataClientError
from stockmarkpred.reporting import append_signal_log, render_dashboard
from stockmarkpred.strategy import PennyMomentumStrategy


class SignalRunner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = AlpacaDataClient(settings)
        self.strategy = PennyMomentumStrategy(settings)

    def _run_cycle(self) -> tuple[list, int]:
        candidate_symbols, snapshots = self.client.build_universe()
        ideas = []

        for symbol in candidate_symbols:
            bars = self.client.get_intraday_bars(symbol, self.settings.bar_lookback)
            if not bars:
                continue
            snapshot = snapshots.get(symbol)
            if snapshot is None:
                continue
            idea = self.strategy.evaluate(snapshot, bars)
            if idea is not None:
                ideas.append(idea)

        ideas.sort(key=lambda item: (item.action != "BUY", -item.score, -item.relative_volume))
        return ideas[: self.settings.max_ideas], len(candidate_symbols)

    def run(self, once: bool = False, max_cycles: int | None = None) -> int:
        cycle_number = 0
        while True:
            cycle_number += 1
            cycle_time = datetime.now(UTC)
            try:
                ideas, scanned_count = self._run_cycle()
                print(render_dashboard(ideas, scanned_count, cycle_time))
                append_signal_log(self.settings.log_path, ideas)
            except KeyboardInterrupt:
                print("\nInterrupted.", file=sys.stderr)
                return 130
            except DataClientError as exc:
                print(f"[cycle {cycle_number}] data error: {exc}", file=sys.stderr)
            except Exception as exc:  # pragma: no cover - defensive guard for long-running jobs.
                print(f"[cycle {cycle_number}] unexpected error: {exc}", file=sys.stderr)

            if once:
                return 0
            if max_cycles is not None and cycle_number >= max_cycles:
                return 0
            if self.settings.verbose:
                print(f"Waiting {self.settings.poll_seconds} seconds for the next scan...\n")
            time.sleep(self.settings.poll_seconds)
