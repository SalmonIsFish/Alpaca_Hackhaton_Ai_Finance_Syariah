"""Verify the account-level Shariah gate rejects margin-enabled accounts.

A margin-capable account carries a standing Riba exposure regardless of
whether any single order actually draws on margin -- see Riba.md in
E:\\Projects Stuff\\Multi_Ai_IslamicFinance\\01-Shariah-Principles and the
"reject leverage/margin" rule in that project's risk-policy.md. This gate is
account-level, separate from option_structure_gate's per-structure checks,
because it must also block plain equity orders through a margin account.
"""

from account_shariah_gate import check_account


def main() -> None:
    cash = check_account(account_type="CASH")
    assert cash["status"] == "PASS"
    assert cash["reason"] == "cash_account_no_margin_exposure"

    margin = check_account(account_type="MARGIN")
    assert margin["status"] == "REJECT"
    assert margin["reason"] == "margin_account_not_permitted"

    # Fail closed on anything not explicitly recognized -- an Alpaca account
    # default (multiplier=4) is MARGIN, so unknown must never default to PASS.
    unknown = check_account(account_type="UNKNOWN")
    assert unknown["status"] == "REJECT"
    assert unknown["reason"] == "unknown_account_type"

    empty = check_account(account_type="")
    assert empty["status"] == "REJECT"
    assert empty["reason"] == "unknown_account_type"

    # Case/whitespace insensitive, matching option_structure_gate's convention.
    normalized = check_account(account_type="  cash ")
    assert normalized["status"] == "PASS"

    print("PASS: account Shariah gate rejects margin exposure and fails closed.")


if __name__ == "__main__":
    main()
