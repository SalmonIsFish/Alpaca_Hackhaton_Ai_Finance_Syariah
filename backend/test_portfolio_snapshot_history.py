"""Verify portfolio value snapshots are throttled and returned oldest-first."""

import sqlite3
from datetime import datetime, timedelta, timezone

from portfolio_store import (
    ensure_portfolio_tables,
    list_portfolio_snapshots,
    record_portfolio_snapshot,
)


def make_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


def backdate_snapshot(connection: sqlite3.Connection, *, minutes_ago: float, account_equity: float) -> None:
    """Insert a snapshot row directly, bypassing the throttle, to simulate one
    captured `minutes_ago` -- lets the throttle test control time without a
    network-style seam."""
    ensure_portfolio_tables(connection)
    captured_at = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()
    connection.execute(
        """
        INSERT INTO portfolio_value_snapshots (
            captured_at, account_equity, market_value, cost_basis, unrealized_pnl, realized_pnl, position_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (captured_at, account_equity, 0, 0, 0, 0, 0),
    )
    connection.commit()


def sample_snapshot(**overrides) -> dict:
    snapshot = {
        "paper_account_equity": 25000.0,
        "market_value": 1200.5,
        "total_cost_basis": 1000.0,
        "unrealized_pnl": 200.5,
        "total_realized_pnl": 50.0,
        "position_count": 2,
    }
    snapshot.update(overrides)
    return snapshot


def main() -> None:
    connection = make_connection()

    # First call ever: no prior snapshot, throttle can't apply -- always records.
    first = record_portfolio_snapshot(connection, sample_snapshot(paper_account_equity=25000.0))
    assert first is not None
    assert first["account_equity"] == 25000.0
    assert first["market_value"] == 1200.5
    assert first["cost_basis"] == 1000.0
    assert first["unrealized_pnl"] == 200.5
    assert first["realized_pnl"] == 50.0
    assert first["position_count"] == 2

    # Immediately after: within the default 15-minute window -- throttled, returns None.
    throttled = record_portfolio_snapshot(connection, sample_snapshot(paper_account_equity=99999.0))
    assert throttled is None

    rows = connection.execute("SELECT COUNT(*) AS n FROM portfolio_value_snapshots").fetchone()
    assert rows["n"] == 1, "a throttled call must not insert a row"

    # Force a custom, shorter throttle to confirm the parameter is honored, not
    # just the default.
    still_throttled = record_portfolio_snapshot(connection, sample_snapshot(), throttle_minutes=60.0)
    assert still_throttled is None

    connection2 = make_connection()
    backdate_snapshot(connection2, minutes_ago=20, account_equity=10000.0)
    stale = record_portfolio_snapshot(connection2, sample_snapshot(paper_account_equity=11000.0))
    assert stale is not None, "a snapshot older than the throttle window must record"
    assert stale["account_equity"] == 11000.0

    history = list_portfolio_snapshots(connection2)
    assert len(history) == 2
    assert history[0]["account_equity"] == 10000.0, "oldest first"
    assert history[1]["account_equity"] == 11000.0

    limited = list_portfolio_snapshots(connection2, limit=1)
    assert len(limited) == 1
    assert limited[0]["account_equity"] == 11000.0, "limit keeps the most recent rows"

    print("PASS: portfolio value snapshots throttle correctly and list oldest-first.")


if __name__ == "__main__":
    main()
