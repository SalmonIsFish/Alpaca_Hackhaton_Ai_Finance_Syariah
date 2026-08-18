"""Verify the account Shariah agent normalizes the gate result correctly."""

from agents.account_shariah_agent import evaluate_account


def main() -> None:
    passed = evaluate_account(account_type="CASH")
    assert passed["agent"] == "account_shariah"
    assert passed["status"] == "PASS"
    assert passed["reason"] == "cash_account_no_margin_exposure"

    rejected = evaluate_account(account_type="MARGIN")
    assert rejected["agent"] == "account_shariah"
    assert rejected["status"] == "REJECT"
    assert rejected["reason"] == "margin_account_not_permitted"

    print("PASS: account Shariah agent normalizes gate results.")


if __name__ == "__main__":
    main()
