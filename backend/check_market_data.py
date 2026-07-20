"""Verify market data for the quant agent without printing API secrets."""

import argparse

from market_data import summarize_history


def main() -> int:
    parser = argparse.ArgumentParser(description="Check quant-agent market data history")
    parser.add_argument("symbol", help="Ticker symbol, for example AAPL")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--min-bars", type=int, default=200)
    parser.add_argument("--strict", action="store_true", help="fail instead of using fixture fallback")
    args = parser.parse_args()

    try:
        summary = summarize_history(
            args.symbol,
            days=args.days,
            min_bars=args.min_bars,
            allow_fallback=not args.strict,
        )
    except Exception as exc:
        print(f"Market data request failed: {type(exc).__name__}")
        return 3

    print(f"Symbol: {summary['symbol']}")
    print(f"Source: {summary['source']}")
    print(f"Bars: {summary['bars']}")
    print(f"Minimum bars: {summary['min_bars']}")
    print(f"Enough history: {summary['enough_history']}")
    print(f"Latest date: {summary['latest_date']}")
    print(f"Latest close: {summary['latest_close']}")
    if not summary["enough_history"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
