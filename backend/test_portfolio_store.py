"""Verify paper portfolio positions are built from filled reconciliations."""

import json
import sqlite3

from approval_queue import record_approval, record_broker_reconciliation
from portfolio_store import portfolio_snapshot, sync_filled_order


def make_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


def add_filled_order(connection: sqlite3.Connection, *, price: float, order_id: str, side: str = "BUY") -> dict:
    preview = {
        "status": "READY_FOR_APPROVAL",
        "execution": "PAPER_ONLY",
        "broker_submission": False,
        "symbol": "AAPL",
        "side": side,
        "quantity": 1,
        "price": 333.74,
        "notional": 333.74,
        "agent_summary": {
            "shariah": {"status": "PASS", "market": "US", "provider": "ZOYA"},
            "quant": {"status": "PASS", "signal": "BUY"},
            "risk": {"status": "PASS"},
        },
    }
    approval = {
        "status": "APPROVED_PAPER_READY",
        "broker_submission": False,
        "execution_environment": "SIMULATE",
    }
    queue_id = record_approval(connection, preview=preview, approval=approval, approved_by_user=True)["id"]
    reconciliation = {
        "status": "BROKER_FILLED",
        "adapter": "moomoo",
        "broker_submission": True,
        "broker_order_id": order_id,
        "broker_code": "US.AAPL",
        "order_status": "FILLED_ALL",
        "side": side,
        "quantity": 1.0,
        "price": 333.74,
        "dealt_qty": 1.0,
        "dealt_avg_price": price,
        "environment": "SIMULATE",
        "account_type": "MARGIN",
        "account_suffix": "1740",
        "updated_at_broker": "2026-07-24 09:30:03",
    }
    record_broker_reconciliation(connection, queue_id, reconciliation=reconciliation)
    row = connection.execute("SELECT * FROM approval_queue WHERE id = ?", (queue_id,)).fetchone()
    return dict(row)


def main() -> None:
    connection = make_connection()
    first = add_filled_order(connection, price=321.86, order_id="ORDER-1")

    first_sync = sync_filled_order(connection, first)
    assert first_sync["status"] == "POSITION_SYNCED"
    assert first_sync["position"]["quantity"] == 1.0
    assert first_sync["position"]["average_cost"] == 321.86
    assert first_sync["position"]["cost_basis"] == 321.86

    duplicate_sync = sync_filled_order(connection, first)
    assert duplicate_sync["status"] == "ALREADY_SYNCED"

    second = add_filled_order(connection, price=300.0, order_id="ORDER-2")
    second_sync = sync_filled_order(connection, second)
    assert second_sync["status"] == "POSITION_SYNCED"
    assert second_sync["position"]["quantity"] == 2.0
    assert second_sync["position"]["average_cost"] == 310.93
    assert second_sync["position"]["cost_basis"] == 621.86

    partial_sell = add_filled_order(connection, price=350.0, order_id="ORDER-3", side="SELL")
    partial_sell_sync = sync_filled_order(connection, partial_sell)
    assert partial_sell_sync["status"] == "POSITION_SYNCED"
    assert partial_sell_sync["position"]["quantity"] == 1.0
    assert partial_sell_sync["position"]["average_cost"] == 310.93
    assert partial_sell_sync["position"]["cost_basis"] == 310.93
    assert partial_sell_sync["position"]["realized_pnl"] == 39.07

    snapshot = portfolio_snapshot(
        connection,
        price_lookup=lambda symbol: {
            "symbol": symbol,
            "source": "test_price",
            "latest_date": "2026-07-24",
            "latest_close": 350.0,
        },
    )
    assert snapshot["position_count"] == 1
    assert snapshot["fill_count"] == 3
    assert snapshot["total_cost_basis"] == 310.93
    assert snapshot["total_realized_pnl"] == 39.07
    assert snapshot["market_value"] == 350.0
    assert snapshot["total_exposure"] == 350.0
    assert snapshot["unrealized_pnl"] == 39.07
    assert snapshot["valuation_status"] == "VALUED"
    assert snapshot["positions"][0]["symbol"] == "AAPL"
    assert snapshot["positions"][0]["latest_price"] == 350.0
    assert snapshot["positions"][0]["market_value"] == 350.0
    assert snapshot["positions"][0]["unrealized_pnl"] == 39.07
    assert snapshot["positions"][0]["exposure_weight_pct"] == 100.0

    final_sell = add_filled_order(connection, price=300.0, order_id="ORDER-4", side="SELL")
    final_sell_sync = sync_filled_order(connection, final_sell)
    assert final_sell_sync["status"] == "POSITION_SYNCED"
    assert final_sell_sync["position"]["quantity"] == 0.0
    assert final_sell_sync["position"]["cost_basis"] == 0.0
    assert final_sell_sync["position"]["realized_pnl"] == 28.14

    closed_snapshot = portfolio_snapshot(connection)
    assert closed_snapshot["position_count"] == 0
    assert closed_snapshot["fill_count"] == 4
    assert closed_snapshot["total_cost_basis"] == 0
    assert closed_snapshot["total_realized_pnl"] == 28.14

    payload = json.loads(connection.execute("SELECT payload FROM paper_fills WHERE queue_id = ?", (first["id"],)).fetchone()["payload"])
    assert payload["broker_order_id"] == "ORDER-1"
    print("PASS: paper portfolio ledger syncs filled orders idempotently.")


if __name__ == "__main__":
    main()
