"""Preview a paper order with a caller-supplied limit price. Places nothing.

/paper/preview already accepts a manual price: agent_coordinator.evaluate_candidate
does ``selected_price = price if price is not None else quant.get("price")``. This
script is a readable front end for that, so the request shape does not have to be
hand-built as JSON on the command line.

Read-only by construction: it calls /paper/preview and nothing else. It cannot
approve and cannot execute -- those are approve_paper_order.py and, only with a
human typing the confirmation phrase, execute_paper_order.py.

    python backend/check_paper_order.py CVX --limit 207.40
    python backend/check_paper_order.py CVX              # auto price from the quote

The reviewed preview is saved so the approval step approves exactly what was shown
here, rather than re-running the quote and approving a slightly different price.
"""

import argparse
import json
from pathlib import Path

from fastapi.testclient import TestClient

import local_api
from alpaca_paper_adapter import check_alpaca_status

BACKEND_DIR = Path(__file__).resolve().parent

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("symbol")
parser.add_argument("--limit", type=float, default=None, help="limit price; omit to use the quote")
parser.add_argument("--qty", type=int, default=1)
parser.add_argument("--position-pct", type=float, default=0.5)
parser.add_argument("--total-exposure-pct", type=float, default=1.0)
parser.add_argument("--loss-per-trade-pct", type=float, default=0.2)
parser.add_argument("--daily-loss-pct", type=float, default=0.3)
parser.add_argument("--orders-today", type=int, default=0)
args = parser.parse_args()

symbol = args.symbol.strip().upper()

status = check_alpaca_status()
print(f"account   {status.get('account_suffix')} type={status.get('account_type')} cash={status.get('cash')}")
if status.get("account_type") != "CASH":
    print("\nNote: account does not report CASH; account_shariah_gate will reject at approval.")

body = {
    "symbol": symbol,
    "side": "BUY",
    "quantity": args.qty,
    "position_pct": args.position_pct,
    "total_exposure_pct": args.total_exposure_pct,
    "loss_per_trade_pct": args.loss_per_trade_pct,
    "daily_loss_pct": args.daily_loss_pct,
    "orders_today": args.orders_today,
}
if args.limit is not None:
    body["price"] = args.limit

client = TestClient(local_api.app)
preview = client.post("/paper/preview", json=body).json().get("preview", {})
summary = preview.get("agent_summary", {})
quant = summary.get("quant", {})

print(f"\n--- PREVIEW  status={preview.get('status')}")
print(f"  price     {preview.get('price')}   (quote said {quant.get('price')} via {quant.get('price_source')})")
print(f"  notional  {preview.get('notional')}")
print(f"  shariah   {summary.get('shariah', {}).get('status')} - {summary.get('shariah', {}).get('reason')}")
print(f"  quant     {quant.get('signal')}")
print(f"  risk      {summary.get('risk', {}).get('status')}")

if preview.get("status") != "READY_FOR_APPROVAL":
    print("\nBLOCKED:")
    for message in preview.get("blocker_messages", []) or []:
        print(f"  - {message.get('blocker')}: {message.get('message')}")
    raise SystemExit(1)

staged = BACKEND_DIR / f"staged_preview_{symbol}.json"
staged.write_text(json.dumps(preview, indent=2, default=str), encoding="utf-8")

print(f"\nNothing has been approved and nothing has reached the broker.")
print(f"Saved the reviewed preview to {staged}")
print("\nNext, to approve it (still no broker contact):\n")
print(f"  .venv\\Scripts\\python.exe backend\\approve_paper_order.py {symbol}")
print("\nThat prints a queue_id and the execute command, which will ask you to type")
print("the confirmation phrase yourself.")
