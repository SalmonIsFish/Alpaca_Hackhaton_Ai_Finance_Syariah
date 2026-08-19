"""Submit an approved paper order, after a human types the confirmation phrase.

This is the only script here that can reach the broker, and it cannot do so on its
own: the confirmation phrase is read from the keyboard and is deliberately not
written anywhere in this file. It is passed through unchanged to
/paper/execute/{queue_id}, which does its own comparison -- this script never
checks, defaults, or supplies it.

CLAUDE.md: "a human must type a confirmation phrase before anything reaches the
broker." That is what the input() call below is for. Do not add a --phrase
argument, an environment variable, or a default; any of those would defeat it.

    python backend/execute_paper_order.py 7
"""

import argparse

from fastapi.testclient import TestClient

import local_api

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("queue_id", type=int)
args = parser.parse_args()

client = TestClient(local_api.app)

approvals = client.get("/approvals").json()
rows = approvals.get("approvals", approvals) if isinstance(approvals, dict) else approvals
match = None
for row in rows if isinstance(rows, list) else []:
    if row.get("id") == args.queue_id:
        match = row
        break

if match is not None:
    print(f"queue {args.queue_id}: {match.get('symbol')} {match.get('side')} "
          f"{match.get('quantity')} @ {match.get('price')}  "
          f"approval={match.get('approval_status')} execution={match.get('execution_status')}")
else:
    print(f"queue {args.queue_id}: could not read the queue row; the endpoint will still validate it.")

print("\nThis submits a real order to the Alpaca paper account.")
phrase = input("Type the confirmation phrase to submit (anything else aborts): ")

response = client.post(f"/paper/execute/{args.queue_id}", json={"confirmation_phrase": phrase})
result = response.json()

print(f"\n--- EXECUTE  status={result.get('status')}")
if result.get("status") == "CONFIRMATION_REQUIRED":
    print("  Not submitted: the phrase did not match.")
    raise SystemExit(1)

for key in ["adapter", "broker_submission", "reason", "execution_message", "executed_at"]:
    if key in result:
        print(f"  {key}: {result[key]}")

print(f"\nThen reconcile with:  POST /paper/reconcile/{args.queue_id}")
