# StockMarkPred

StockMarkPred is a live, rules-based penny-stock scanner for intraday momentum trading. It polls Alpaca market-data endpoints, ranks exchange-traded stocks priced under a configurable cap, and prints suggested long ideas with a stop loss, take profit, confidence score, and the exact indicators that drove each decision.

This build does not pretend to guarantee profit. It is a transparent screening engine for research and paper trading. Penny stocks are highly volatile, spreads can widen fast, and live execution risk is material.

## Strategy

The scoring model in this project is original in its weighting, but it is built from standard intraday momentum components:

- Gap strength from the previous close.
- Price location versus session VWAP.
- 9 EMA versus 20 EMA trend alignment.
- 14-period RSI for momentum confirmation.
- MACD histogram for short-term acceleration.
- Relative volume versus the recent session baseline.
- Opening-range breakout behavior.
- Spread and dollar-volume checks to avoid illiquid names.

The engine only emits a `BUY` idea when the name remains above VWAP, the fast trend is above the slow trend, and liquidity or momentum are good enough to clear the score threshold. Otherwise it either emits `WATCH` or ignores the symbol.

## Data Source

The live client is built around Alpaca's official market-data API:

- Historical bars: <https://docs.alpaca.markets/reference/stockbarsingle>
- Snapshots: <https://docs.alpaca.markets/reference/stocksnapshots-1>
- Top movers: <https://docs.alpaca.markets/reference/movers-1>
- Most actives: <https://docs.alpaca.markets/v1.3/reference/mostactives>
- Real-time stock feeds overview: <https://docs.alpaca.markets/docs/real-time-stock-pricing-data>

Indicator behavior is based on standard technical-analysis definitions. For reference:

- ATR: <https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/atr>
- MACD: <https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/macd>
- RSI: <https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/RSI>
- Average volume: <https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/average-volume>

## Files

- `main.py`: CLI entrypoint.
- `stockmarkpred/config.py`: environment parsing and runtime settings.
- `stockmarkpred/data.py`: Alpaca REST client and universe construction.
- `stockmarkpred/indicators.py`: indicator calculations.
- `stockmarkpred/strategy.py`: signal scoring and risk logic.
- `stockmarkpred/reporting.py`: console dashboard and JSONL logging.
- `stockmarkpred/runner.py`: continuous scan loop.
- `tests/`: small unit tests for indicator math and signal behavior.

## Setup

1. Copy `.env.example` to `.env`.
2. Add your Alpaca market-data API key and secret.
3. Run the scanner with your Python 3.11 path:

```powershell
C:/Users/rushi/AppData/Local/Microsoft/WindowsApps/python3.11.exe main.py --once
```

To keep it running:

```powershell
C:/Users/rushi/AppData/Local/Microsoft/WindowsApps/python3.11.exe main.py
```

Useful overrides:

```powershell
C:/Users/rushi/AppData/Local/Microsoft/WindowsApps/python3.11.exe main.py --poll-seconds 20 --candidate-limit 18 --max-ideas 6
```

Add manual symbols on top of the live screener:

```powershell
C:/Users/rushi/AppData/Local/Microsoft/WindowsApps/python3.11.exe main.py --symbols AEMD SINT
```

## Output

Each cycle prints:

- ranked symbols
- `BUY` or `WATCH`
- score and confidence
- last price
- suggested entry, stop, and take-profit
- gap percentage
- relative volume
- top decision reasons

Every emitted idea is also appended to `outputs/signals.jsonl`.

## Notes

- Alpaca's free feed is usually `iex`, not the full SIP feed. The default `.env.example` uses `iex`.
- This scanner only covers symbols Alpaca serves. Many OTC penny stocks are not included.
- Outside regular U.S. market hours, the scanner will still evaluate the latest session it can fetch, which may be stale.
