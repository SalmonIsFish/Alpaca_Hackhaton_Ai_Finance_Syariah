"""Structured approval queue storage for paper orders."""

import json
import sqlite3
from datetime import datetime, timezone


def ensure_approval_queue(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS approval_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            quantity INTEGER,
            price REAL,
            notional REAL,
            approval_status TEXT NOT NULL,
            execution_environment TEXT,
            broker_submission INTEGER NOT NULL,
            shariah_status TEXT,
            shariah_market TEXT,
            quant_signal TEXT,
            risk_status TEXT,
            payload TEXT NOT NULL
        )
        """
    )
    connection.commit()


def record_approval(connection: sqlite3.Connection, *, preview: dict, approval: dict, approved_by_user: bool) -> dict:
    ensure_approval_queue(connection)
    created_at = datetime.now(timezone.utc).isoformat()
    agents = preview.get("agent_summary", {})
    shariah = agents.get("shariah", preview.get("shariah", {}))
    quant = agents.get("quant", {})
    risk = agents.get("risk", preview.get("risk", {}))
    status = approval.get("status", "UNKNOWN")
    payload = {
        "approved_by_user": approved_by_user,
        "preview": preview,
        "approval": approval,
    }
    cursor = connection.execute(
        """
        INSERT INTO approval_queue (
            created_at,
            symbol,
            side,
            quantity,
            price,
            notional,
            approval_status,
            execution_environment,
            broker_submission,
            shariah_status,
            shariah_market,
            quant_signal,
            risk_status,
            payload
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            created_at,
            preview.get("symbol") or "",
            preview.get("side") or "BUY",
            preview.get("quantity"),
            preview.get("price"),
            preview.get("notional"),
            status,
            approval.get("execution_environment"),
            1 if approval.get("broker_submission") else 0,
            shariah.get("status"),
            shariah.get("market"),
            quant.get("signal"),
            risk.get("status"),
            json.dumps(payload, sort_keys=True),
        ),
    )
    connection.commit()
    return {"id": cursor.lastrowid, "created_at": created_at, "approval_status": status}


def list_approvals(connection: sqlite3.Connection, *, limit: int = 100) -> list[dict]:
    ensure_approval_queue(connection)
    rows = connection.execute(
        """
        SELECT
            id,
            created_at,
            symbol,
            side,
            quantity,
            price,
            notional,
            approval_status,
            execution_environment,
            broker_submission,
            shariah_status,
            shariah_market,
            quant_signal,
            risk_status,
            payload
        FROM approval_queue
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    approvals = []
    for row in rows:
        item = dict(row)
        item["broker_submission"] = bool(item["broker_submission"])
        approvals.append(item)
    return approvals
