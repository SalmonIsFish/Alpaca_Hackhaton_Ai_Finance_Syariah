"""Select a Level 1 option contract without creating an order.

Read-only: it pulls the live chain and prints what the strategy layer would propose,
including the rationale. It never builds an approval and never touches the broker.

    python backend/check_option_strategy.py AAPL --shares 100
    python backend/check_option_strategy.py AAPL --cash 25000
"""

import argparse
import json


from market_data import summarize_history
from option_strategy import select_cash_secured_put, select_covered_call


parser = argparse.ArgumentParser()
parser.add_argument("symbol")
parser.add_argument("--shares", type=int, default=0, help="settled shares held, for a covered call")
parser.add_argument("--cash", type=float, default=0.0, help="settled cash, for a cash-secured put")
parser.add_argument("--spot", type=float, default=None, help="override the spot price instead of fetching it")
parser.add_argument("--min-dte", type=int, default=None)
parser.add_argument("--max-dte", type=int, default=None)
parser.add_argument("--target-otm", type=float, default=None, help="target %% out of the money")
args = parser.parse_args()

spot = args.spot
if spot is None:
    summary = summarize_history(args.symbol, days=30, min_bars=1)
    spot = summary.get("latest_close")
    print(f"Spot: {spot} (source: {summary.get('source')}, {summary.get('bars')} bars)")

policy = {"min_dte": args.min_dte, "max_dte": args.max_dte, "target_otm_pct": args.target_otm}

if args.shares:
    result = select_covered_call(args.symbol, shares_held=args.shares, spot=spot, policy=policy)
elif args.cash:
    result = select_cash_secured_put(args.symbol, cash_available=args.cash, spot=spot, policy=policy)
else:
    parser.error("give --shares (covered call) or --cash (cash-secured put)")

print(json.dumps({key: value for key, value in result.items() if key != "rationale"}, indent=2, default=str))
if result.get("rationale"):
    print()
    print(result["rationale"])
