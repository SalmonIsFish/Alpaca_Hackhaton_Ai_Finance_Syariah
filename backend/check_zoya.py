"""Check Zoya compliance without exposing the API key."""

import argparse

from zoya_compliance import check_us_symbol


parser = argparse.ArgumentParser()
parser.add_argument("symbol", help="US ticker, for example AAPL")
args = parser.parse_args()
print(check_us_symbol(args.symbol))
