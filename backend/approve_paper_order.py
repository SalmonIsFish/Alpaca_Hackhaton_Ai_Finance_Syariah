"""Approve the preview staged by check_paper_order.py. Reaches no broker.

/paper/approval runs the full gate chain -- shariah_gate, option_structure_gate,
account_shariah_gate, then approval_workflow -- and always returns
broker_submission: False. Approving is not submitting; only /paper/execute with the
confirmation phrase reaches Alpaca.

    python backend/approve_paper_order.py CVX

It approves the preview that check_paper_order.py saved, not a freshly re-quoted
one, so what is approved is exactly what was reviewed.
"""

import argparse
import json
from pathlib import Path

from fastapi.testclient import TestClient

import local_api

BACKEND_DIR = Path(__file__).resolve().parent

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("symbol")
args = parser.parse_args()

symbol = args.symbol.strip().upper()
staged = BACKEND_DIR / f"staged_preview_{symbol}.json"
if not staged.exists():
    raise SystemExit(f"no staged preview at {staged}; run check_paper_order.py {symbol} first")

preview = json.loads(staged.read_text(encoding="utf-8"))
print(f"approving the staged preview: {symbol} {preview.get('side')} "
      f"{preview.get('quantity')} @ {preview.get('price')}")

client = TestClient(local_api.app)
envelope = client.post("/paper/approval", json={"preview": preview, "approved": True}).json()
approval = envelope.get("approval", {})
queue_id = envelope.get("queue_id")

print(f"\n--- APPROVAL  status={approval.get('status')}  reason={approval.get('reason')}")
print(f"  queue_id  {queue_id}")
print(f"  broker_submission  {approval.get('broker_submission')}")
print(f"  trace     {approval.get('shariah_trace')}")

if approval.get("status") != "APPROVED_PAPER_READY":
    print("\nRejected by the gate chain. Nothing to execute.")
    raise SystemExit(1)

print("\nStill nothing has reached the broker.")
print("\nTo submit, run this and type the confirmation phrase when prompted:\n")
print(f"  .venv\\Scripts\\python.exe backend\\execute_paper_order.py {queue_id}")
