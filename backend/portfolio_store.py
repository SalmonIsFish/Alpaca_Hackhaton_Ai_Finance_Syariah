"""Local paper portfolio ledger built from filled broker reconciliations."""

import json
import sqlite3
from datetime import datetime, timezone


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_portfolio_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS paper_fills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            queue_id INTEGER NOT NULL UNIQUE,
            broker_order_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            quantity REAL NOT NULL,
            avg_price REAL NOT NULL,
            notional REAL NOT NULL,
            filled_at TEXT NOT NULL,
            account_suffix TEXT,
            account_type TEXT,
            payload TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS paper_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            account_suffix TEXT NOT NULL,
            account_type TEXT,
            quantity REAL NOT NULL,
            average_cost REAL NOT NULL,
            cost_basis REAL NOT NULL,
            realized_pnl REAL NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(symbol, account_suffix)
        )
        """
    )
    connection.commit()


def extract_latest_reconciliation(approval: dict) -> dict | None:
    payload = approval.get("payload")
    parsed = {}
    if isinstance(payload, str):
        try:
            parsed = json.loads(payload)
        except (TypeError, json.JSONDecodeError):
            parsed = {}
    elif isinstance(payload, dict):
        parsed = payload
    reconciliation = parsed.get("broker_reconciliation")
    if isinstance(reconciliation, dict):
        return reconciliation
    return None


def sync_filled_order(connection: sqlite3.Connection, approval: dict) -> dict:
    ensure_portfolio_tables(connection)
    queue_id = approval.get("id")
    reconciliation = extract_latest_reconciliation(approval)
    if not reconciliation or reconciliation.get("status") != "BROKER_FILLED":
        return {"status": "NOT_FILLED", "queue_id": queue_id, "position_updated": False}

    existing = connection.execute("SELECT id FROM paper_fills WHERE queue_id = ?", (queue_id,)).fetchone()
    if existing is not None:
        return {"status": "ALREADY_SYNCED", "queue_id": queue_id, "position_updated": False}

    quantity = float(reconciliation.get("dealt_qty") or reconciliation.get("quantity") or 0)
    avg_price = float(reconciliation.get("dealt_avg_price") or reconciliation.get("price") or 0)
    if quantity <= 0 or avg_price <= 0:
        return {"status": "INVALID_FILL", "queue_id": queue_id, "position_updated": False}

    symbol = str(approval.get("symbol") or reconciliation.get("symbol") or reconciliation.get("broker_code") or "").upper()
    side = str(reconciliation.get("side") or approval.get("side") or "BUY").upper()
    account_suffix = str(reconciliation.get("account_suffix") or "UNKNOWN")
    account_type = reconciliation.get("account_type")
    filled_at = reconciliation.get("updated_at_broker") or reconciliation.get("reconciled_at") or utc_now()
    broker_order_id = str(reconciliation.get("broker_order_id") or approval.get("execution_message") or "")
    notional = round(quantity * avg_price, 4)

    if side == "SELL":
        position = connection.execute(
            """
            SELECT COALESCE(quantity, 0) AS quantity
            FROM paper_positions
            WHERE symbol = ? AND account_suffix = ?
            """,
            (symbol, account_suffix),
        ).fetchone()
        available_quantity = round(float(position["quantity"] or 0), 4) if position else 0.0
        if available_quantity <= 0 or quantity > available_quantity:
            return {
                "status": "INVALID_SELL_FILL",
                "queue_id": queue_id,
                "position_updated": False,
                "reason": "sell_fill_exceeds_local_position",
                "symbol": symbol,
                "requested_quantity": quantity,
                "available_quantity": available_quantity,
                "account_suffix": account_suffix,
            }

    connection.execute(
        """
        INSERT INTO paper_fills (
            queue_id,
            broker_order_id,
            symbol,
            side,
            quantity,
            avg_price,
            notional,
            filled_at,
            account_suffix,
            account_type,
            payload
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            queue_id,
            broker_order_id,
            symbol,
            side,
            quantity,
            avg_price,
            notional,
            filled_at,
            account_suffix,
            account_type,
            json.dumps(reconciliation, sort_keys=True),
        ),
    )
    position = apply_fill_to_position(
        connection,
        symbol=symbol,
        account_suffix=account_suffix,
        account_type=account_type,
        side=side,
        quantity=quantity,
        avg_price=avg_price,
    )
    connection.commit()
    return {
        "status": "POSITION_SYNCED",
        "queue_id": queue_id,
        "position_updated": True,
        "fill": {
            "broker_order_id": broker_order_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "avg_price": avg_price,
            "notional": notional,
            "filled_at": filled_at,
            "account_suffix": account_suffix,
            "account_type": account_type,
        },
        "position": position,
    }


def apply_fill_to_position(
    connection: sqlite3.Connection,
    *,
    symbol: str,
    account_suffix: str,
    account_type: str | None,
    side: str,
    quantity: float,
    avg_price: float,
) -> dict:
    now = utc_now()
    row = connection.execute(
        """
        SELECT quantity, average_cost, cost_basis, realized_pnl
        FROM paper_positions
        WHERE symbol = ? AND account_suffix = ?
        """,
        (symbol, account_suffix),
    ).fetchone()
    current_qty = float(row["quantity"]) if row else 0.0
    current_avg = float(row["average_cost"]) if row else 0.0
    current_cost = float(row["cost_basis"]) if row else 0.0
    realized_pnl = float(row["realized_pnl"]) if row else 0.0

    if side == "SELL":
        sell_qty = min(quantity, current_qty)
        realized_pnl += round((avg_price - current_avg) * sell_qty, 4)
        new_qty = max(current_qty - quantity, 0.0)
        new_cost = round(new_qty * current_avg, 4)
        new_avg = current_avg if new_qty else 0.0
    else:
        new_qty = current_qty + quantity
        new_cost = round(current_cost + quantity * avg_price, 4)
        new_avg = round(new_cost / new_qty, 4) if new_qty else 0.0

    connection.execute(
        """
        INSERT INTO paper_positions (
            symbol,
            account_suffix,
            account_type,
            quantity,
            average_cost,
            cost_basis,
            realized_pnl,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, account_suffix) DO UPDATE SET
            account_type = excluded.account_type,
            quantity = excluded.quantity,
            average_cost = excluded.average_cost,
            cost_basis = excluded.cost_basis,
            realized_pnl = excluded.realized_pnl,
            updated_at = excluded.updated_at
        """,
        (symbol, account_suffix, account_type, new_qty, new_avg, new_cost, realized_pnl, now),
    )
    return {
        "symbol": symbol,
        "account_suffix": account_suffix,
        "account_type": account_type,
        "quantity": new_qty,
        "average_cost": new_avg,
        "cost_basis": new_cost,
        "realized_pnl": round(realized_pnl, 4),
        "updated_at": now,
    }


def open_position_quantity(connection: sqlite3.Connection, *, symbol: str, account_suffix: str | None = None) -> float:
    ensure_portfolio_tables(connection)
    normalized_symbol = symbol.strip().upper()
    if account_suffix:
        row = connection.execute(
            """
            SELECT COALESCE(SUM(quantity), 0) AS quantity
            FROM paper_positions
            WHERE symbol = ? AND account_suffix = ? AND quantity > 0
            """,
            (normalized_symbol, str(account_suffix)),
        ).fetchone()
    else:
        row = connection.execute(
            """
            SELECT COALESCE(SUM(quantity), 0) AS quantity
            FROM paper_positions
            WHERE symbol = ? AND quantity > 0
            """,
            (normalized_symbol,),
        ).fetchone()
    return round(float(row["quantity"] or 0), 4)


def portfolio_snapshot(connection: sqlite3.Connection, *, price_lookup=None) -> dict:
    ensure_portfolio_tables(connection)
    positions = [
        dict(row)
        for row in connection.execute(
            """
            SELECT symbol, account_suffix, account_type, quantity, average_cost, cost_basis, realized_pnl, updated_at
            FROM paper_positions
            WHERE quantity != 0
            ORDER BY symbol, account_suffix
            """
        ).fetchall()
    ]
    valuation_errors = []
    for position in positions:
        position["latest_price"] = None
        position["price_source"] = None
        position["price_date"] = None
        position["market_value"] = None
        position["unrealized_pnl"] = None
        position["unrealized_pnl_pct"] = None
        position["exposure_weight_pct"] = None
        if price_lookup is None:
            continue
        try:
            price = price_lookup(position["symbol"])
        except Exception as exc:
            error = {
                "symbol": position["symbol"],
                "status": "DATA_ERROR",
                "reason": type(exc).__name__,
            }
            valuation_errors.append(error)
            position["valuation_status"] = "DATA_ERROR"
            position["valuation_error"] = error
            continue
        latest_price = price.get("latest_close")
        if latest_price is None:
            error = {
                "symbol": position["symbol"],
                "status": "DATA_ERROR",
                "reason": "latest_close_missing",
            }
            valuation_errors.append(error)
            position["valuation_status"] = "DATA_ERROR"
            position["valuation_error"] = error
            continue
        quantity = float(position["quantity"])
        cost_basis = float(position["cost_basis"])
        market_value = round(quantity * float(latest_price), 4)
        unrealized_pnl = round(market_value - cost_basis, 4)
        position["latest_price"] = float(latest_price)
        position["price_source"] = price.get("source")
        position["price_date"] = price.get("latest_date")
        position["market_value"] = market_value
        position["unrealized_pnl"] = unrealized_pnl
        position["unrealized_pnl_pct"] = round((unrealized_pnl / cost_basis) * 100, 4) if cost_basis else None
        position["valuation_status"] = "VALUED"

    fills = [
        dict(row)
        for row in connection.execute(
            """
            SELECT queue_id, broker_order_id, symbol, side, quantity, avg_price, notional, filled_at, account_suffix, account_type
            FROM paper_fills
            ORDER BY id DESC
            LIMIT 50
            """
        ).fetchall()
    ]
    total_cost_basis = round(sum(float(position["cost_basis"]) for position in positions), 4)
    realized_row = connection.execute("SELECT COALESCE(SUM(realized_pnl), 0) AS total_realized_pnl FROM paper_positions").fetchone()
    total_realized_pnl = round(float(realized_row["total_realized_pnl"] or 0), 4)
    valued_positions = [position for position in positions if position.get("market_value") is not None]
    market_value = round(sum(float(position["market_value"]) for position in valued_positions), 4) if valued_positions else None
    unrealized_pnl = round(sum(float(position["unrealized_pnl"]) for position in valued_positions), 4) if valued_positions else None
    if market_value:
        for position in positions:
            if position.get("market_value") is not None:
                position["exposure_weight_pct"] = round((float(position["market_value"]) / market_value) * 100, 4)

    valuation_status = "NOT_REQUESTED"
    if price_lookup is not None:
        valuation_status = "EMPTY" if not positions else "VALUED" if valued_positions and not valuation_errors else "PARTIAL" if valued_positions else "DATA_ERROR"

    return {
        "status": "OK",
        "valuation_status": valuation_status,
        "positions": positions,
        "fills": fills,
        "position_count": len(positions),
        "fill_count": len(fills),
        "total_cost_basis": total_cost_basis,
        "total_realized_pnl": total_realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "market_value": market_value,
        "total_exposure": market_value,
        "valuation_errors": valuation_errors,
        "updated_at": utc_now(),
    }
