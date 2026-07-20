"""Check the Tiingo adapter without exposing the API token."""

import argparse
from datetime import date, timedelta

from tiingo_prices import fetch_eod_prices


parser = argparse.ArgumentParser()
parser.add_argument("symbol", help="Tiingo symbol, for example AAPL")
parser.add_argument("--strict", action="store_true", help="fail instead of using fixture fallback")
args = parser.parse_args()

end = date.today()
start = end - timedelta(days=30)
try:
    bars, source = fetch_eod_prices(args.symbol, start.isoformat(), end.isoformat(), allow_fallback=not args.strict)
    print(f"Price source: {source}")
    print(f"Bars returned: {len(bars)}")
    print(bars[-1] if bars else "No bars returned")
except Exception as exc:
    print(f"Tiingo request failed: {type(exc).__name__}")
    raise SystemExit(1)
