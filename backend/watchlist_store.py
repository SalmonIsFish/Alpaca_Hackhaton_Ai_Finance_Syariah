"""SQLite persistence for watchlist settings and opportunity alerts."""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Iterable

from opportunity_scanner import DEFAULT_WATCHLIST, parse_symbols


TRACKED_ALERT_STATES = {"NOT_READY", "NEAR_BREAKOUT", "ALERT", "READY"}
INITIAL_ALERT_STATES = {"ALERT", "READY"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_watchlist_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS watchlist_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            symbols TEXT NOT NULL,
            alert_threshold_pct REAL NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS opportunity_scan_results (
            symbol TEXT PRIMARY KEY,
            scan_id INTEGER,
            scanned_at TEXT NOT NULL,
            event_status TEXT NOT NULL,
            watch_status TEXT NOT NULL,
            alert_status TEXT NOT NULL,
            ready_for_approval INTEGER NOT NULL,
            price REAL,
            trigger_price REAL,
            breakout_gap_pct REAL,
            payload TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS opportunity_alert_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            symbol TEXT NOT NULL,
            previous_status TEXT,
            new_status TEXT NOT NULL,
            scan_id INTEGER,
            payload TEXT NOT NULL
        )
        """
    )
    connection.commit()


def normalize_symbols(symbols: str | Iterable[str] | None) -> list[str]:
    if symbols is None:
        return list(DEFAULT_WATCHLIST)
    if isinstance(symbols, str):
        return parse_symbols(symbols)
    return parse_symbols(",".join(str(symbol) for symbol in symbols))


def get_watchlist_settings(connection: sqlite3.Connection) -> dict:
    ensure_watchlist_tables(connection)
    row = connection.execute(
        "SELECT symbols, alert_threshold_pct, updated_at FROM watchlist_settings WHERE id = 1"
    ).fetchone()
    if row is None:
        symbols = list(DEFAULT_WATCHLIST)
        return {
            "symbols": symbols,
            "alert_threshold_pct": 3.0,
            "updated_at": None,
            "latest_results": list_latest_scan_results(connection, symbols=symbols),
        }
    symbols = json.loads(row["symbols"])
    return {
        "symbols": symbols,
        "alert_threshold_pct": row["alert_threshold_pct"],
        "updated_at": row["updated_at"],
        "latest_results": list_latest_scan_results(connection, symbols=symbols),
    }


def save_watchlist_settings(
    connection: sqlite3.Connection,
    *,
    symbols: str | Iterable[str],
    alert_threshold_pct: float,
) -> dict:
    ensure_watchlist_tables(connection)
    parsed_symbols = normalize_symbols(symbols)
    threshold = max(0.1, min(20.0, float(alert_threshold_pct)))
    updated_at = utc_now()
    connection.execute(
        """
        INSERT INTO watchlist_settings (id, symbols, alert_threshold_pct, updated_at)
        VALUES (1, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            symbols = excluded.symbols,
            alert_threshold_pct = excluded.alert_threshold_pct,
            updated_at = excluded.updated_at
        """,
        (json.dumps(parsed_symbols), threshold, updated_at),
    )
    connection.commit()
    return {
        "symbols": parsed_symbols,
        "alert_threshold_pct": threshold,
        "updated_at": updated_at,
        "latest_results": list_latest_scan_results(connection, symbols=parsed_symbols),
    }


def event_status(item: dict) -> str:
    if item.get("ready_for_approval") is True:
        return "READY"
    if item.get("alert_status") == "ALERT":
        return "ALERT"
    return item.get("watch_status") or "NOT_READY"


def save_opportunity_scan(
    connection: sqlite3.Connection,
    *,
    scan_id: int,
    scanned_at: str,
    scan: dict,
) -> list[dict]:
    ensure_watchlist_tables(connection)
    events = []
    for item in scan.get("items", []):
        symbol = item["symbol"]
        new_status = event_status(item)
        previous = connection.execute(
            "SELECT event_status FROM opportunity_scan_results WHERE symbol = ?",
            (symbol,),
        ).fetchone()
        previous_status = previous["event_status"] if previous else None
        record_event = should_record_transition(previous_status, new_status)
        event_previous_status = previous_status
        if not record_event and should_backfill_current_alert(connection, symbol, previous_status, new_status):
            record_event = True
            event_previous_status = None
        if record_event:
            payload = {
                "symbol": symbol,
                "previous_status": event_previous_status,
                "new_status": new_status,
                "watch_status": item.get("watch_status"),
                "alert_status": item.get("alert_status"),
                "price": item.get("price"),
                "trigger_price": item.get("trigger_price"),
                "blockers": item.get("blockers", []),
                "error_type": item.get("error_type"),
            }
            cursor = connection.execute(
                """
                INSERT INTO opportunity_alert_events (
                    created_at, symbol, previous_status, new_status, scan_id, payload
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    scanned_at,
                    symbol,
                    event_previous_status,
                    new_status,
                    scan_id,
                    json.dumps(payload, sort_keys=True),
                ),
            )
            events.append({"id": cursor.lastrowid, "created_at": scanned_at, **payload})

        connection.execute(
            """
            INSERT INTO opportunity_scan_results (
                symbol,
                scan_id,
                scanned_at,
                event_status,
                watch_status,
                alert_status,
                ready_for_approval,
                price,
                trigger_price,
                breakout_gap_pct,
                payload
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                scan_id = excluded.scan_id,
                scanned_at = excluded.scanned_at,
                event_status = excluded.event_status,
                watch_status = excluded.watch_status,
                alert_status = excluded.alert_status,
                ready_for_approval = excluded.ready_for_approval,
                price = excluded.price,
                trigger_price = excluded.trigger_price,
                breakout_gap_pct = excluded.breakout_gap_pct,
                payload = excluded.payload
            """,
            (
                symbol,
                scan_id,
                scanned_at,
                new_status,
                item.get("watch_status") or "NOT_READY",
                item.get("alert_status") or "NONE",
                1 if item.get("ready_for_approval") else 0,
                item.get("price"),
                item.get("trigger_price"),
                item.get("breakout_gap_pct"),
                json.dumps(item, sort_keys=True),
            ),
        )
    connection.commit()
    return events


def latest_scan_snapshot(connection: sqlite3.Connection, *, symbols: Iterable[str] | None = None) -> dict | None:
    latest_results = list_latest_scan_results(connection, symbols=symbols)
    items = [row["payload"] for row in latest_results if row.get("payload")]
    scanned_at_values = [row["scanned_at"] for row in latest_results if row.get("scanned_at")]
    if not items or not scanned_at_values:
        return None
    latest_scanned_at = max(scanned_at_values)
    return {
        "created_at": latest_scanned_at,
        "count": len(items),
        "ready_count": sum(1 for item in items if item.get("ready_for_approval")),
        "alert_count": sum(1 for item in items if item.get("alert_status") == "ALERT"),
        "data_error_count": sum(1 for item in items if item.get("watch_status") == "DATA_ERROR"),
        "items": items,
    }


def should_record_transition(previous_status: str | None, new_status: str) -> bool:
    if previous_status is None:
        return new_status in INITIAL_ALERT_STATES
    if previous_status == new_status:
        return False
    return previous_status in TRACKED_ALERT_STATES or new_status in TRACKED_ALERT_STATES


def should_backfill_current_alert(
    connection: sqlite3.Connection,
    symbol: str,
    previous_status: str | None,
    new_status: str,
) -> bool:
    if previous_status != new_status or new_status not in INITIAL_ALERT_STATES:
        return False
    row = connection.execute(
        """
        SELECT id
        FROM opportunity_alert_events
        WHERE symbol = ? AND new_status = ?
        LIMIT 1
        """,
        (symbol, new_status),
    ).fetchone()
    return row is None


def list_latest_scan_results(
    connection: sqlite3.Connection,
    *,
    limit: int = 100,
    symbols: Iterable[str] | None = None,
) -> list[dict]:
    ensure_watchlist_tables(connection)
    active_symbols = normalize_symbols(symbols) if symbols is not None else None
    rows = connection.execute(
        """
        SELECT
            symbol,
            scan_id,
            scanned_at,
            event_status,
            watch_status,
            alert_status,
            ready_for_approval,
            price,
            trigger_price,
            breakout_gap_pct,
            payload
        FROM opportunity_scan_results
        ORDER BY scanned_at DESC, symbol ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    results = []
    for row in rows:
        if active_symbols is not None and row["symbol"] not in active_symbols:
            continue
        item = dict(row)
        item["ready_for_approval"] = bool(item["ready_for_approval"])
        try:
            item["payload"] = json.loads(item["payload"])
        except (TypeError, json.JSONDecodeError):
            item["payload"] = {}
        results.append(item)
    if active_symbols is None:
        return results
    order = {symbol: index for index, symbol in enumerate(active_symbols)}
    return sorted(results, key=lambda item: order.get(item["symbol"], len(order)))


def list_alert_events(connection: sqlite3.Connection, *, limit: int = 50) -> list[dict]:
    ensure_watchlist_tables(connection)
    rows = connection.execute(
        """
        SELECT id, created_at, symbol, previous_status, new_status, scan_id, payload
        FROM opportunity_alert_events
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    events = []
    for row in rows:
        event = dict(row)
        try:
            event["payload"] = json.loads(event["payload"])
        except (TypeError, json.JSONDecodeError):
            event["payload"] = {}
        events.append(event)
    return events
