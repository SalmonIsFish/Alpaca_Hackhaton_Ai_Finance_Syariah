"""Fail-closed Shariah gate for account-level margin/Riba exposure.

Separate from option_structure_gate.py's per-structure checks: this gate
blocks trading through a margin-enabled account outright, including plain
equity orders, because carrying margin capability at all is a standing Riba
exposure regardless of whether a given order draws on it. See Riba.md and
hackathon/alpaca-2026/SHARIAH_GATE_NOTES.md.
"""


def check_account(*, account_type: str) -> dict:
    normalized = str(account_type or "").strip().upper()
    if normalized == "CASH":
        return {"status": "PASS", "reason": "cash_account_no_margin_exposure"}
    if normalized == "MARGIN":
        return {"status": "REJECT", "reason": "margin_account_not_permitted"}
    return {"status": "REJECT", "reason": "unknown_account_type"}
