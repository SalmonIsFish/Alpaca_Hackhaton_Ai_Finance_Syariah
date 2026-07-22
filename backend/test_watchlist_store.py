"""Verify watchlist persistence and opportunity alert transitions."""

import sqlite3

from watchlist_store import (
    get_watchlist_settings,
    list_alert_events,
    list_latest_scan_results,
    save_opportunity_scan,
    save_watchlist_settings,
)


def make_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return connection


def scan_with_status(symbol: str, *, watch_status: str, alert_status: str = "NONE", ready: bool = False) -> dict:
    return {
        "count": 1,
        "ready_count": 1 if ready else 0,
        "alert_count": 1 if alert_status == "ALERT" else 0,
        "data_error_count": 0,
        "items": [
            {
                "symbol": symbol,
                "decision": "READY_FOR_APPROVAL" if ready else "BLOCKED",
                "ready_for_approval": ready,
                "blockers": [] if ready else ["quant_no_buy_signal"],
                "price": 100.0,
                "trigger_price": 102.0,
                "breakout_gap_pct": -1.9,
                "watch_status": watch_status,
                "alert_status": alert_status,
            }
        ],
    }


def data_error_scan(symbol: str) -> dict:
    return {
        "count": 1,
        "ready_count": 0,
        "alert_count": 0,
        "data_error_count": 1,
        "items": [
            {
                "symbol": symbol,
                "decision": "BLOCKED",
                "ready_for_approval": False,
                "blockers": ["market_data_unavailable"],
                "price": None,
                "trigger_price": None,
                "breakout_gap_pct": None,
                "watch_status": "DATA_ERROR",
                "alert_status": "DATA_ERROR",
                "error_type": "URLError",
                "error_code": "url_error",
                "error_message": "Tiingo network error: temporary failure",
            }
        ],
    }


def main() -> None:
    connection = make_connection()

    defaults = get_watchlist_settings(connection)
    assert defaults["symbols"]
    assert defaults["alert_threshold_pct"] == 3.0
    assert defaults["latest_results"] == []

    saved = save_watchlist_settings(
        connection,
        symbols=["aapl", "AAPL", "panw"],
        alert_threshold_pct=2.5,
    )
    assert saved["symbols"] == ["AAPL", "PANW"]
    assert saved["alert_threshold_pct"] == 2.5

    first_alert_connection = make_connection()
    first_alert_events = save_opportunity_scan(
        first_alert_connection,
        scan_id=10,
        scanned_at="2026-07-22T00:00:00+00:00",
        scan=scan_with_status("PANW", watch_status="NEAR_BREAKOUT", alert_status="ALERT"),
    )
    assert len(first_alert_events) == 1
    assert first_alert_events[0]["previous_status"] is None
    assert first_alert_events[0]["new_status"] == "ALERT"
    assert list_alert_events(first_alert_connection)[0]["previous_status"] is None

    first_events = save_opportunity_scan(
        connection,
        scan_id=1,
        scanned_at="2026-07-22T00:00:00+00:00",
        scan=scan_with_status("AAPL", watch_status="NOT_READY"),
    )
    assert first_events == []
    latest = list_latest_scan_results(connection)
    assert len(latest) == 1
    assert latest[0]["symbol"] == "AAPL"
    assert latest[0]["event_status"] == "NOT_READY"
    assert latest[0]["ready_for_approval"] is False

    alert_events = save_opportunity_scan(
        connection,
        scan_id=2,
        scanned_at="2026-07-22T00:01:00+00:00",
        scan=scan_with_status("AAPL", watch_status="NEAR_BREAKOUT", alert_status="ALERT"),
    )
    assert len(alert_events) == 1
    assert alert_events[0]["previous_status"] == "NOT_READY"
    assert alert_events[0]["new_status"] == "ALERT"

    repeated_events = save_opportunity_scan(
        connection,
        scan_id=3,
        scanned_at="2026-07-22T00:02:00+00:00",
        scan=scan_with_status("AAPL", watch_status="NEAR_BREAKOUT", alert_status="ALERT"),
    )
    assert repeated_events == []

    ready_events = save_opportunity_scan(
        connection,
        scan_id=4,
        scanned_at="2026-07-22T00:03:00+00:00",
        scan=scan_with_status("AAPL", watch_status="READY", alert_status="TRIGGERED", ready=True),
    )
    assert len(ready_events) == 1
    assert ready_events[0]["previous_status"] == "ALERT"
    assert ready_events[0]["new_status"] == "READY"

    events = list_alert_events(connection)
    assert [event["new_status"] for event in events] == ["READY", "ALERT"]
    assert events[0]["symbol"] == "AAPL"
    assert events[0]["payload"]["trigger_price"] == 102.0

    data_error_events = save_opportunity_scan(
        connection,
        scan_id=5,
        scanned_at="2026-07-22T00:04:00+00:00",
        scan=data_error_scan("AAPL"),
    )
    assert len(data_error_events) == 1
    assert data_error_events[0]["previous_status"] == "READY"
    assert data_error_events[0]["new_status"] == "DATA_ERROR"
    assert data_error_events[0]["error_type"] == "URLError"
    assert list_alert_events(connection)[0]["payload"]["error_type"] == "URLError"

    stale_connection = make_connection()
    save_opportunity_scan(
        stale_connection,
        scan_id=30,
        scanned_at="2026-07-22T00:00:00+00:00",
        scan={
            "items": [
                scan_with_status("AAPL", watch_status="NEAR_BREAKOUT", alert_status="ALERT")["items"][0],
                scan_with_status("PANW", watch_status="NEAR_BREAKOUT", alert_status="ALERT")["items"][0],
            ]
        },
    )
    narrowed = save_watchlist_settings(
        stale_connection,
        symbols=["AAPL"],
        alert_threshold_pct=3.0,
    )
    assert [row["symbol"] for row in narrowed["latest_results"]] == ["AAPL"]
    reloaded = get_watchlist_settings(stale_connection)
    assert [row["symbol"] for row in reloaded["latest_results"]] == ["AAPL"]

    legacy_connection = make_connection()
    save_opportunity_scan(
        legacy_connection,
        scan_id=20,
        scanned_at="2026-07-22T00:00:00+00:00",
        scan=scan_with_status("CRM", watch_status="NOT_READY"),
    )
    save_opportunity_scan(
        legacy_connection,
        scan_id=21,
        scanned_at="2026-07-22T00:01:00+00:00",
        scan=scan_with_status("CRM", watch_status="NEAR_BREAKOUT", alert_status="ALERT"),
    )
    legacy_connection.execute("DELETE FROM opportunity_alert_events")
    legacy_connection.commit()
    backfill_events = save_opportunity_scan(
        legacy_connection,
        scan_id=22,
        scanned_at="2026-07-22T00:02:00+00:00",
        scan=scan_with_status("CRM", watch_status="NEAR_BREAKOUT", alert_status="ALERT"),
    )
    assert len(backfill_events) == 1
    assert backfill_events[0]["previous_status"] is None
    assert backfill_events[0]["new_status"] == "ALERT"

    print("PASS: watchlist persistence and alert transitions are durable.")


if __name__ == "__main__":
    main()
