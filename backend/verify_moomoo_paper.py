"""Verify that OpenD exposes an active cash paper account.

This script is read-only. It never places, modifies, or cancels an order.
"""

import sys

try:
    from moomoo import OpenSecTradeContext
except ModuleNotFoundError as exc:  # pragma: no cover - environment check
    print("Moomoo SDK is not installed in this Python environment.")
    print("Install it with: python -m pip install moomoo-api")
    raise SystemExit(3) from exc


HOST = "127.0.0.1"
PORT = 11111


def main() -> int:
    context = OpenSecTradeContext(host=HOST, port=PORT)
    try:
        ret, accounts = context.get_acc_list()
        if ret != 0:
            print(f"OpenD account query failed: {ret}")
            return 1

        paper = accounts[
            (accounts["trd_env"] == "SIMULATE")
            & (accounts["acc_type"] == "CASH")
            & (accounts["acc_status"] == "ACTIVE")
        ]

        if paper.empty:
            print("SAFE STOP: no active SIMULATE CASH account was found.")
            print("No real account was selected and no order was submitted.")
            return 2

        account_id = str(paper.iloc[0]["acc_id"])
        print("PAPER ACCOUNT VERIFIED")
        print(f"Environment: {paper.iloc[0]['trd_env']}")
        print(f"Account type: {paper.iloc[0]['acc_type']}")
        print(f"Status: {paper.iloc[0]['acc_status']}")
        print(f"Account suffix: ...{account_id[-4:]}")
        print("Real accounts were ignored. No order was submitted.")
        return 0
    finally:
        context.close()


if __name__ == "__main__":
    sys.exit(main())
