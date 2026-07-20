"""Run price retrieval through the Shariah gate and S001 strategy."""

import argparse
from datetime import date, timedelta

from strategy_engine import evaluate_s001
from tiingo_prices import fetch_eod_prices


parser = argparse.ArgumentParser()
parser.add_argument("symbol")
args = parser.parse_args()
end = date.today()
bars, source = fetch_eod_prices(args.symbol, (end - timedelta(days=365)).isoformat(), end.isoformat())
result = evaluate_s001(args.symbol, bars)
print(f"Price source: {source}")
print(result)
