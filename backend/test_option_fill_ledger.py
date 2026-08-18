"""An option fill must never be booked as shares of its underlying."""

import json
import sqlite3

from portfolio_store import (
    OPTION_CONTRACT_MULTIPLIER,
    ensure_portfolio_tables,
    is_option_fill,
    open_position_quantity,
    sync_filled_order,
)


COVERED_CALL_RECONCILIATION = {
    "status": "BROKER_FILLED",
    "adapter": "alpaca_mcp",
    "broker_submission": True,
    "broker_order_id": "ALPACA-OPT-77",
    "broker_code": "AAPL260918C00350000",
    "asset_class": "option",
    "side": "SELL",
    "dealt_qty": 2.0,
    "dealt_avg_price": 4.35,
    "account_suffix": "0TCX",
    "account_type": "MARGIN",
    "updated_at_broker": "2026-08-18T14:00:00Z",
}


EQUITY_RECONCILIATION = {
    "status": "BROKER_FILLED",
    "adapter": "alpaca",
    "broker_submission": True,
    "broker_order_id": "ALPACA-EQ-78",
    "broker_code": "AAPL",
    "asset_class": "equity",
    "side": "BUY",
    "dealt_qty": 3.0,
    "dealt_avg_price": 195.45,
    "account_suffix": "0TCX",
    "account_type": "MARGIN",
    "updated_at_broker": "2026-08-18T14:05:00Z",
}


def make_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    ensure_portfolio_tables(connection)
    return connection


def approval(queue_id: int, reconciliation: dict, *, side: str, symbol: str = "AAPL") -> dict:
    return {
        "id": queue_id,
        "symbol": symbol,
        "side": side,
        "payload": json.dumps({"broker_reconciliation": reconciliation}),
    }


def check_option_detection() -> None:
    assert is_option_fill(COVERED_CALL_RECONCILIATION) is True
    assert is_option_fill(EQUITY_RECONCILIATION) is False
    # Detected from the OCC symbol even when asset_class is absent.
    assert is_option_fill({"broker_code": "AAPL260918C00350000"}) is True
    assert is_option_fill({"broker_code": "MSFT261016P00402500"}) is True
    assert is_option_fill({"broker_code": "AAPL"}) is False
    assert is_option_fill({}) is False


def check_option_fill_does_not_touch_equity_ledger() -> None:
    connection = make_connection()
    try:
        result = sync_filled_order(connection, approval(77, COVERED_CALL_RECONCILIATION, side="SELL"))
        assert result["status"] == "OPTION_FILL_RECORDED", result
        assert result["position_updated"] is False

        # The critical assertion: no phantom AAPL shares, in either direction.
        assert open_position_quantity(connection, symbol="AAPL", account_suffix="0TCX") == 0
        rows = connection.execute("SELECT COUNT(*) AS n FROM paper_positions").fetchone()
        assert rows["n"] == 0, "an option fill must create no equity position row"

        # It is still audited, under the contract symbol rather than the underlying.
        fill = connection.execute("SELECT * FROM paper_fills WHERE queue_id = 77").fetchone()
        assert fill is not None, "the option fill must still be recorded for audit"
        assert fill["symbol"] == "AAPL260918C00350000"
        assert fill["quantity"] == 2.0
        assert fill["notional"] == round(2.0 * 4.35 * OPTION_CONTRACT_MULTIPLIER, 4) == 870.0

        assert result["fill"]["underlying"] == "AAPL"
        assert result["fill"]["contracts"] == 2.0
        assert result["fill"]["contract_multiplier"] == OPTION_CONTRACT_MULTIPLIER

        # Re-syncing stays idempotent.
        assert sync_filled_order(connection, approval(77, COVERED_CALL_RECONCILIATION, side="SELL"))["status"] == "ALREADY_SYNCED"
    finally:
        connection.close()


def check_equity_fill_still_books_normally() -> None:
    connection = make_connection()
    try:
        result = sync_filled_order(connection, approval(78, EQUITY_RECONCILIATION, side="BUY"))
        assert result["status"] == "POSITION_SYNCED", result
        assert result["position_updated"] is True
        assert open_position_quantity(connection, symbol="AAPL", account_suffix="0TCX") == 3.0
    finally:
        connection.close()


def check_option_and_equity_ledgers_stay_separate() -> None:
    connection = make_connection()
    try:
        sync_filled_order(connection, approval(78, EQUITY_RECONCILIATION, side="BUY"))
        sync_filled_order(connection, approval(77, COVERED_CALL_RECONCILIATION, side="SELL"))

        # Selling 2 calls against 3 shares must leave the share count untouched.
        assert open_position_quantity(connection, symbol="AAPL", account_suffix="0TCX") == 3.0
        symbols = [row["symbol"] for row in connection.execute("SELECT symbol FROM paper_positions").fetchall()]
        assert symbols == ["AAPL"], symbols
        fills = sorted(row["symbol"] for row in connection.execute("SELECT symbol FROM paper_fills").fetchall())
        assert fills == ["AAPL", "AAPL260918C00350000"], fills
    finally:
        connection.close()


def main() -> None:
    check_option_detection()
    check_option_fill_does_not_touch_equity_ledger()
    check_equity_fill_still_books_normally()
    check_option_and_equity_ledgers_stay_separate()
    print("PASS: option fills are audited without corrupting the equity position ledger.")


if __name__ == "__main__":
    main()
