"""Run the US pipeline without creating an order."""

import argparse
from datetime import date, timedelta

from tiingo_prices import fetch_eod_prices
from us_strategy import evaluate_us_s001


parser = argparse.ArgumentParser()
parser.add_argument("symbol")
args = parser.parse_args()
end = date.today()
bars, source = fetch_eod_prices(args.symbol, (end - timedelta(days=365)).isoformat(), end.isoformat())
print(f"Price source: {source}")
print(evaluate_us_s001(args.symbol, bars))
