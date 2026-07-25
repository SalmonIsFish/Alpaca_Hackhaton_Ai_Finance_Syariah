"""Minimal local API for the paper-trading dashboard."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent_coordinator import evaluate_candidate
from agents.shariah_agent import detect_market, evaluate_shariah
from approval_queue import ensure_approval_queue, get_approval, list_approvals, record_approval
from approval_workflow import approve_candidate
from config import load_settings
from market_data import summarize_history
from moomoo_status import check_moomoo_status
from opportunity_scanner import scan_opportunities
from paper_execution import execute_paper_order, reconcile_submitted_paper_order
from portfolio_store import ensure_portfolio_tables, portfolio_snapshot, sync_filled_order
from trading_modes import trading_mode_status
from watchlist_store import (
    ensure_watchlist_tables,
    get_watchlist_settings,
    list_latest_scan_results,
    latest_scan_snapshot,
    list_alert_events,
    save_opportunity_scan,
    save_watchlist_settings,
)


BACKEND_DIR = Path(__file__).resolve().parent
DB_PATH = BACKEND_DIR / "paper_trading.db"
app = FastAPI(title="Amanah Trader Local API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE IF NOT EXISTS audit_events (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, event_type TEXT NOT NULL, payload TEXT NOT NULL)")
    ensure_approval_queue(connection)
    ensure_watchlist_tables(connection)
    ensure_portfolio_tables(connection)
    connection.commit()
    return connection


def broker_submission_configured(settings) -> bool:
    return settings.paper_execution_enabled and settings.paper_execution_adapter in {"fake", "moomoo"}


class PaperPreviewRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    side: str = "BUY"
    quantity: int = Field(gt=0, le=1_000_000)
    price: float | None = Field(default=None, gt=0)
    position_pct: float = Field(ge=0)
    total_exposure_pct: float = Field(ge=0)
    loss_per_trade_pct: float = Field(ge=0)
    daily_loss_pct: float = Field(ge=0)
    orders_today: int = Field(ge=0)
    test_fixture: bool = False


class PaperApprovalRequest(BaseModel):
    preview: dict
    approved: bool


class PaperExecutionRequest(BaseModel):
    confirmation_phrase: str | None = None


class WatchlistRequest(BaseModel):
    symbols: list[str] = Field(min_length=1, max_length=30)
    alert_threshold_pct: float = Field(ge=0.1, le=20.0)


PAPER_EXECUTION_CONFIRMATION = "EXECUTE PAPER"
DEFAULT_SCAN_THROTTLE_MINUTES = 10
PAPER_TEST_SYMBOLS = {"AAPL"}


def add_audit_event(event_type: str, payload: dict) -> dict:
    created_at = datetime.now(timezone.utc).isoformat()
    connection = db()
    try:
        cursor = connection.execute(
            "INSERT INTO audit_events (created_at, event_type, payload) VALUES (?, ?, ?)",
            (created_at, event_type, json.dumps(payload, sort_keys=True)),
        )
        connection.commit()
        return {"id": cursor.lastrowid, "created_at": created_at, "event_type": event_type}
    finally:
        connection.close()


def paper_test_overrides(request: PaperPreviewRequest) -> dict:
    if not request.test_fixture:
        return {}

    settings = load_settings()
    symbol = request.symbol.strip().upper()
    if (
        symbol not in PAPER_TEST_SYMBOLS
        or settings.moomoo_mode != "paper"
        or settings.trading_mode != "approval"
        or not settings.paper_execution_enabled
    ):
        return {}

    price = request.price or 1.0
    return {
        "shariah_override": {
            "agent": "shariah",
            "market": "US",
            "provider": "PAPER_TEST_FIXTURE",
            "status": "PASS",
            "symbol": symbol,
            "reason": "paper_execution_test_fixture",
            "details": {"status": "COMPLIANT", "symbol": symbol, "fixture": True},
        },
        "quant_override": {
            "agent": "quant",
            "status": "PASS",
            "symbol": symbol,
            "signal": "BUY",
            "reason": "paper_execution_test_fixture",
            "price": price,
            "bars": 220,
            "price_source": "paper_test_fixture",
            "strategy": {
                "signal": "BUY",
                "sma50": price,
                "sma200": round(price * 0.95, 4),
                "trend_ok": True,
                "breakout_ok": True,
                "breakout_level": round(price * 0.99, 4),
                "breakout_gap_pct": 1.0101,
            },
        },
    }


def portfolio_price_lookup(symbol: str) -> dict:
    return summarize_history(
        symbol,
        days=14,
        min_bars=1,
        allow_fallback=False,
        allow_stale_cache=True,
    )


def exposure_value(position: dict) -> float:
    value = position.get("market_value")
    if value is None:
        value = position.get("cost_basis")
    return float(value or 0)


def add_exposure_metadata(snapshot: dict, *, account_equity: float) -> dict:
    total_exposure = round(sum(exposure_value(position) for position in snapshot.get("positions", [])), 4)
    snapshot["paper_account_equity"] = account_equity
    snapshot["total_exposure"] = total_exposure
    snapshot["total_exposure_pct"] = round((total_exposure / account_equity) * 100, 4)
    for position in snapshot.get("positions", []):
        value = exposure_value(position)
        position["exposure_value"] = round(value, 4)
        position["account_exposure_pct"] = round((value / account_equity) * 100, 4)
    return snapshot


def portfolio_snapshot_with_exposure(connection: sqlite3.Connection) -> dict:
    settings = load_settings()
    snapshot = add_exposure_metadata(
        portfolio_snapshot(connection, price_lookup=portfolio_price_lookup),
        account_equity=settings.paper_account_equity,
    )
    snapshot["risk_limits"] = risk_limits_from_settings(settings)
    return snapshot


def positions_snapshot(connection: sqlite3.Connection) -> dict:
    portfolio = portfolio_snapshot_with_exposure(connection)
    limits = portfolio.get("risk_limits", {})
    max_position_pct = float(limits.get("max_position_pct") or 0)
    positions = []
    for position in portfolio.get("positions", []):
        quantity = round(float(position.get("quantity") or 0), 4)
        account_exposure_pct = round(float(position.get("account_exposure_pct") or 0), 4)
        valuation_status = position.get("valuation_status") or portfolio.get("valuation_status")
        positions.append(
            {
                "symbol": position.get("symbol"),
                "account_suffix": position.get("account_suffix"),
                "account_type": position.get("account_type"),
                "quantity": quantity,
                "average_cost": position.get("average_cost"),
                "cost_basis": position.get("cost_basis"),
                "latest_price": position.get("latest_price"),
                "price_source": position.get("price_source"),
                "price_date": position.get("price_date"),
                "market_value": position.get("market_value"),
                "unrealized_pnl": position.get("unrealized_pnl"),
                "unrealized_pnl_pct": position.get("unrealized_pnl_pct"),
                "realized_pnl": position.get("realized_pnl"),
                "exposure_value": position.get("exposure_value"),
                "account_exposure_pct": account_exposure_pct,
                "exposure_weight_pct": position.get("exposure_weight_pct"),
                "position_limit_status": "PASS" if account_exposure_pct <= max_position_pct else "BREACH",
                "valuation_status": valuation_status,
                "valuation_error": position.get("valuation_error"),
                "reduce_eligible": quantity > 0,
                "max_reduce_quantity": quantity,
                "updated_at": position.get("updated_at"),
            }
        )
    return {
        "status": "OK",
        "positions": positions,
        "position_count": len(positions),
        "paper_account_equity": portfolio.get("paper_account_equity"),
        "total_exposure": portfolio.get("total_exposure"),
        "total_exposure_pct": portfolio.get("total_exposure_pct"),
        "total_exposure_status": "PASS"
        if float(portfolio.get("total_exposure_pct") or 0) <= float(limits.get("max_total_exposure_pct") or 0)
        else "BREACH",
        "risk_limits": limits,
        "valuation_status": portfolio.get("valuation_status"),
        "valuation_errors": portfolio.get("valuation_errors", []),
        "updated_at": portfolio.get("updated_at"),
    }


def hours_since_iso(value: str | None) -> float | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return round((datetime.now(timezone.utc) - parsed).total_seconds() / 3600, 2)


def increment_count(counts: dict, key: str | None) -> None:
    label = key or "unknown"
    counts[label] = counts.get(label, 0) + 1


def compact_market_candidate(row: dict) -> dict:
    item = row.get("payload") or {}
    return {
        "symbol": row.get("symbol") or item.get("symbol"),
        "watch_status": row.get("watch_status") or item.get("watch_status"),
        "alert_status": row.get("alert_status") or item.get("alert_status"),
        "ready_for_approval": bool(row.get("ready_for_approval") or item.get("ready_for_approval")),
        "price": row.get("price") if row.get("price") is not None else item.get("price"),
        "trigger_price": row.get("trigger_price") if row.get("trigger_price") is not None else item.get("trigger_price"),
        "breakout_gap_pct": row.get("breakout_gap_pct") if row.get("breakout_gap_pct") is not None else item.get("breakout_gap_pct"),
        "distance_to_trigger": item.get("distance_to_trigger"),
        "shariah_status": item.get("shariah_status"),
        "quant_signal": item.get("quant_signal"),
        "risk_status": item.get("risk_status"),
        "price_source": item.get("price_source"),
        "data_freshness": item.get("data_freshness"),
        "cache_age_hours": item.get("cache_age_hours"),
        "bars": item.get("bars"),
        "blockers": item.get("blockers", []),
        "latest_scan": {
            "scan_id": row.get("scan_id"),
            "scanned_at": row.get("scanned_at"),
            "age_hours": hours_since_iso(row.get("scanned_at")),
            "event_status": row.get("event_status"),
        },
    }


def market_overview_snapshot(connection: sqlite3.Connection, *, stale_cache_hours: float = 24.0) -> dict:
    settings = load_settings()
    watchlist = get_watchlist_settings(connection)
    symbols = watchlist["symbols"]
    latest_results = list_latest_scan_results(connection, symbols=symbols, limit=200)
    result_symbols = {row.get("symbol") for row in latest_results}
    candidates = [compact_market_candidate(row) for row in latest_results]
    portfolio = portfolio_snapshot_with_exposure(connection)
    freshness_counts = {}
    source_counts = {}
    status_counts = {
        "ready": 0,
        "alerts": 0,
        "near_breakout": 0,
        "blocked": 0,
        "data_errors": 0,
        "not_ready": 0,
    }
    stale_cache_symbols = []
    for candidate in candidates:
        watch_status = candidate.get("watch_status")
        if candidate.get("ready_for_approval"):
            status_counts["ready"] += 1
        if candidate.get("alert_status") == "ALERT":
            status_counts["alerts"] += 1
        if watch_status == "NEAR_BREAKOUT":
            status_counts["near_breakout"] += 1
        elif watch_status == "BLOCKED":
            status_counts["blocked"] += 1
        elif watch_status == "DATA_ERROR":
            status_counts["data_errors"] += 1
        elif watch_status == "NOT_READY":
            status_counts["not_ready"] += 1
        increment_count(freshness_counts, candidate.get("data_freshness"))
        increment_count(source_counts, candidate.get("price_source"))
        cache_age = candidate.get("cache_age_hours")
        if cache_age is not None and float(cache_age) > stale_cache_hours:
            stale_cache_symbols.append(candidate["symbol"])

    latest_scan_times = [candidate["latest_scan"]["scanned_at"] for candidate in candidates if candidate["latest_scan"]["scanned_at"]]
    latest_scan_at = max(latest_scan_times) if latest_scan_times else None
    unscanned_symbols = [symbol for symbol in symbols if symbol not in result_symbols]
    ready_candidates = [candidate for candidate in candidates if candidate["ready_for_approval"]]
    alert_candidates = [candidate for candidate in candidates if candidate.get("alert_status") == "ALERT"]
    data_error_candidates = [candidate for candidate in candidates if candidate.get("watch_status") == "DATA_ERROR"]
    return {
        "status": "OK",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "trading_mode": settings.trading_mode,
        "broker_submission": broker_submission_configured(settings),
        "paper_execution_enabled": settings.paper_execution_enabled,
        "watchlist": {
            "symbols": symbols,
            "count": len(symbols),
            "alert_threshold_pct": watchlist["alert_threshold_pct"],
            "updated_at": watchlist["updated_at"],
            "unscanned_symbols": unscanned_symbols,
        },
        "latest_scan": {
            "scanned_at": latest_scan_at,
            "age_hours": hours_since_iso(latest_scan_at),
            "scanned_count": len(candidates),
            "coverage_pct": round((len(candidates) / len(symbols)) * 100, 4) if symbols else 0,
        },
        "counts": status_counts,
        "data_health": {
            "freshness_counts": freshness_counts,
            "source_counts": source_counts,
            "stale_cache_hours": stale_cache_hours,
            "stale_cache_symbols": stale_cache_symbols,
        },
        "portfolio": {
            "open_positions": portfolio.get("position_count", 0),
            "valuation_status": portfolio.get("valuation_status"),
            "total_exposure": portfolio.get("total_exposure"),
            "total_exposure_pct": portfolio.get("total_exposure_pct"),
            "paper_account_equity": portfolio.get("paper_account_equity"),
        },
        "risk_limits": portfolio.get("risk_limits", risk_limits_from_settings(settings)),
        "ready_candidates": ready_candidates[:10],
        "alert_candidates": alert_candidates[:10],
        "data_error_candidates": data_error_candidates[:10],
        "recent_alert_events": list_alert_events(connection, limit=10),
    }


def stock_profile_snapshot(connection: sqlite3.Connection, symbol: str) -> dict:
    normalized_symbol = symbol.strip().upper()
    settings = load_settings()
    profile = {
        "status": "OK" if normalized_symbol else "INVALID_SYMBOL",
        "symbol": normalized_symbol,
        "market": detect_market(normalized_symbol) if normalized_symbol else None,
        "shariah": None,
        "market_data": None,
        "latest_opportunity": None,
        "portfolio": {
            "positions": [],
            "quantity": 0.0,
            "cost_basis": 0.0,
            "market_value": 0.0,
            "unrealized_pnl": 0.0,
            "account_exposure_pct": 0.0,
        },
        "risk_limits": risk_limits_from_settings(settings),
        "errors": [],
    }
    if not normalized_symbol:
        profile["errors"].append({"section": "symbol", "reason": "symbol_required"})
        return profile

    try:
        profile["shariah"] = evaluate_shariah(normalized_symbol)
    except Exception as exc:
        profile["errors"].append({"section": "shariah", "reason": type(exc).__name__})

    try:
        profile["market_data"] = summarize_history(
            normalized_symbol,
            days=365,
            min_bars=200,
            allow_fallback=False,
            allow_stale_cache=True,
        )
    except Exception as exc:
        profile["errors"].append({"section": "market_data", "reason": type(exc).__name__})

    latest_results = list_latest_scan_results(connection, symbols=[normalized_symbol])
    if latest_results:
        profile["latest_opportunity"] = latest_results[0]

    portfolio = portfolio_snapshot_with_exposure(connection)
    positions = [position for position in portfolio.get("positions", []) if position.get("symbol") == normalized_symbol]
    market_value = round(sum(float(position.get("market_value") or 0) for position in positions), 4)
    cost_basis = round(sum(float(position.get("cost_basis") or 0) for position in positions), 4)
    quantity = round(sum(float(position.get("quantity") or 0) for position in positions), 4)
    unrealized_pnl = round(sum(float(position.get("unrealized_pnl") or 0) for position in positions), 4)
    exposure_value_total = round(sum(exposure_value(position) for position in positions), 4)
    profile["portfolio"] = {
        "positions": positions,
        "quantity": quantity,
        "cost_basis": cost_basis,
        "market_value": market_value,
        "unrealized_pnl": unrealized_pnl,
        "account_exposure_pct": round((exposure_value_total / settings.paper_account_equity) * 100, 4),
        "valuation_status": portfolio.get("valuation_status"),
        "valuation_errors": [
            error for error in portfolio.get("valuation_errors", []) if error.get("symbol") == normalized_symbol
        ],
    }
    return profile


def compact_approval(approval: dict) -> dict:
    return {
        "id": approval.get("id"),
        "created_at": approval.get("created_at"),
        "symbol": approval.get("symbol"),
        "side": approval.get("side"),
        "quantity": approval.get("quantity"),
        "price": approval.get("price"),
        "notional": approval.get("notional"),
        "approval_status": approval.get("approval_status"),
        "execution_status": approval.get("execution_status"),
        "execution_message": approval.get("execution_message"),
        "broker_submission": approval.get("broker_submission"),
        "shariah_status": approval.get("shariah_status"),
        "quant_signal": approval.get("quant_signal"),
        "risk_status": approval.get("risk_status"),
    }


def committee_status(item: dict) -> str:
    if item.get("ready_for_approval") is True:
        return "READY_FOR_REVIEW"
    if item.get("watch_status") == "DATA_ERROR":
        return "DATA_ERROR"
    if item.get("alert_status") == "ALERT":
        return "WATCH_ALERT"
    if item.get("blockers"):
        return "BLOCKED"
    return "WATCH"


def investment_committee_snapshot(connection: sqlite3.Connection, *, limit: int = 50) -> dict:
    settings = load_settings()
    watchlist = get_watchlist_settings(connection)
    latest_results = list_latest_scan_results(connection, symbols=watchlist["symbols"], limit=max(1, min(200, limit)))
    approvals = list_approvals(connection, limit=max(1, min(200, limit)))
    portfolio = portfolio_snapshot_with_exposure(connection)

    approvals_by_symbol: dict[str, list[dict]] = {}
    for approval in approvals:
        symbol = str(approval.get("symbol") or "").upper()
        approvals_by_symbol.setdefault(symbol, []).append(compact_approval(approval))

    candidates = []
    for row in latest_results:
        item = row.get("payload") or {}
        symbol = row.get("symbol") or item.get("symbol")
        candidates.append(
            {
                "symbol": symbol,
                "committee_status": committee_status(item),
                "decision": item.get("decision"),
                "ready_for_approval": bool(item.get("ready_for_approval")),
                "blockers": item.get("blockers", []),
                "shariah_status": item.get("shariah_status"),
                "quant_signal": item.get("quant_signal"),
                "risk_status": item.get("risk_status"),
                "watch_status": item.get("watch_status"),
                "alert_status": item.get("alert_status"),
                "price": item.get("price"),
                "trigger_price": item.get("trigger_price"),
                "breakout_gap_pct": item.get("breakout_gap_pct"),
                "latest_scan": {
                    "scan_id": row.get("scan_id"),
                    "scanned_at": row.get("scanned_at"),
                    "event_status": row.get("event_status"),
                },
                "recent_approvals": approvals_by_symbol.get(symbol, [])[:5],
            }
        )

    pending_approvals = [
        compact_approval(approval)
        for approval in approvals
        if approval.get("approval_status") == "APPROVED_PAPER_READY" and not approval.get("broker_submission")
    ]
    submitted_orders = [compact_approval(approval) for approval in approvals if approval.get("broker_submission")]
    return {
        "status": "OK",
        "trading_mode": settings.trading_mode,
        "paper_execution_enabled": settings.paper_execution_enabled,
        "paper_execution_adapter": settings.paper_execution_adapter,
        "broker_submission": broker_submission_configured(settings),
        "watchlist": {
            "symbols": watchlist["symbols"],
            "alert_threshold_pct": watchlist["alert_threshold_pct"],
            "updated_at": watchlist["updated_at"],
        },
        "counts": {
            "candidates": len(candidates),
            "ready_for_review": sum(1 for candidate in candidates if candidate["committee_status"] == "READY_FOR_REVIEW"),
            "watch_alerts": sum(1 for candidate in candidates if candidate["committee_status"] == "WATCH_ALERT"),
            "blocked": sum(1 for candidate in candidates if candidate["committee_status"] == "BLOCKED"),
            "data_errors": sum(1 for candidate in candidates if candidate["committee_status"] == "DATA_ERROR"),
            "pending_approvals": len(pending_approvals),
            "submitted_orders": len(submitted_orders),
            "open_positions": portfolio.get("position_count", 0),
        },
        "risk_limits": risk_limits_from_settings(settings),
        "portfolio": {
            "valuation_status": portfolio.get("valuation_status"),
            "total_exposure": portfolio.get("total_exposure"),
            "total_exposure_pct": portfolio.get("total_exposure_pct"),
            "paper_account_equity": portfolio.get("paper_account_equity"),
            "positions": portfolio.get("positions", []),
        },
        "candidates": candidates,
        "pending_approvals": pending_approvals,
        "submitted_orders": submitted_orders,
    }


def risk_limits_from_settings(settings) -> dict:
    return {
        "max_position_pct": settings.max_position_pct,
        "max_total_exposure_pct": settings.max_total_exposure_pct,
        "max_loss_per_trade_pct": settings.max_loss_per_trade_pct,
        "max_daily_loss_pct": settings.max_daily_loss_pct,
        "max_orders_per_day": settings.max_orders_per_day,
    }


def portfolio_risk_overlay(connection: sqlite3.Connection, request: PaperPreviewRequest, evaluation: dict) -> dict:
    settings = load_settings()
    limits = risk_limits_from_settings(settings)
    symbol = evaluation.get("symbol") or request.symbol.strip().upper()
    side = request.side.strip().upper()
    selected_price = evaluation.get("price") or request.price
    notional = round(request.quantity * selected_price, 4) if selected_price else 0
    snapshot = portfolio_snapshot_with_exposure(connection)
    matching_positions = [position for position in snapshot.get("positions", []) if position.get("symbol") == symbol]
    current_position_exposure = round(
        sum(exposure_value(position) for position in matching_positions),
        4,
    )
    current_position_quantity = round(sum(float(position.get("quantity") or 0) for position in matching_positions), 4)
    current_total_exposure = round(snapshot.get("total_exposure") or 0, 4)
    if side == "SELL":
        projected_position_quantity = max(0, round(current_position_quantity - request.quantity, 4))
        remaining_ratio = projected_position_quantity / current_position_quantity if current_position_quantity else 0
        projected_position_exposure = round(current_position_exposure * remaining_ratio, 4)
        reduced_exposure = round(current_position_exposure - projected_position_exposure, 4)
        projected_total_exposure = max(0, round(current_total_exposure - reduced_exposure, 4))
    else:
        projected_position_quantity = round(current_position_quantity + request.quantity, 4)
        projected_position_exposure = max(0, round(current_position_exposure + notional, 4))
        projected_total_exposure = max(0, round(current_total_exposure + notional, 4))
    projected_position_pct = round((projected_position_exposure / settings.paper_account_equity) * 100, 4)
    projected_total_pct = round((projected_total_exposure / settings.paper_account_equity) * 100, 4)
    effective_position_pct = max(request.position_pct, projected_position_pct)
    effective_total_pct = max(request.total_exposure_pct, projected_total_pct)
    blockers = []
    warnings = []
    messages = {}
    if projected_position_pct > limits["max_position_pct"]:
        blockers.append("portfolio_position_limit")
        messages["portfolio_position_limit"] = f"{symbol} would become {projected_position_pct:.2f}% of paper account equity, above the {limits['max_position_pct']:.2f}% position limit."
    if projected_total_pct > limits["max_total_exposure_pct"]:
        blockers.append("portfolio_total_exposure_limit")
        messages["portfolio_total_exposure_limit"] = f"Total projected exposure would become {projected_total_pct:.2f}% of paper account equity, above the {limits['max_total_exposure_pct']:.2f}% total exposure limit."
    if side == "BUY" and current_position_exposure > 0:
        blockers.append("portfolio_existing_position")
        messages["portfolio_existing_position"] = f"{symbol} is already held locally; same-symbol BUY add-ons are blocked until the risk policy is changed."
    if side == "SELL" and current_position_quantity <= 0:
        blockers.append("portfolio_sell_without_position")
        messages["portfolio_sell_without_position"] = f"{symbol} cannot be sold because no local paper position is recorded."
    if side == "SELL" and current_position_quantity > 0 and request.quantity > current_position_quantity:
        blockers.append("portfolio_sell_exceeds_position")
        messages["portfolio_sell_exceeds_position"] = f"Sell quantity {request.quantity} exceeds the local {symbol} position of {current_position_quantity:g}."
    if side == "SELL" and current_position_quantity > 0 and request.quantity <= current_position_quantity:
        warnings.append("portfolio_reduce_position")
        messages["portfolio_reduce_position"] = f"{symbol} SELL would reduce the local position from {current_position_quantity:g} to {projected_position_quantity:g} shares."
    return {
        "status": "PASS" if not blockers else "REJECT",
        "reason": "portfolio_limits_passed" if not blockers else "portfolio_limit_failed",
        "blockers": blockers,
        "warnings": warnings,
        "messages": messages,
        "account_equity": settings.paper_account_equity,
        "symbol": symbol,
        "side": side,
        "order_notional": notional,
        "current_position_exposure": current_position_exposure,
        "current_position_quantity": current_position_quantity,
        "current_total_exposure": current_total_exposure,
        "projected_position_exposure": projected_position_exposure,
        "projected_position_quantity": projected_position_quantity,
        "projected_total_exposure": projected_total_exposure,
        "submitted_position_pct": request.position_pct,
        "submitted_total_exposure_pct": request.total_exposure_pct,
        "projected_position_pct": projected_position_pct,
        "projected_total_exposure_pct": projected_total_pct,
        "effective_position_pct": round(effective_position_pct, 4),
        "effective_total_exposure_pct": round(effective_total_pct, 4),
        "limits": limits,
        "valuation_status": snapshot.get("valuation_status"),
        "valuation_errors": snapshot.get("valuation_errors", []),
    }


def apply_portfolio_risk_overlay(connection: sqlite3.Connection, request: PaperPreviewRequest, evaluation: dict) -> dict:
    overlay = portfolio_risk_overlay(connection, request, evaluation)
    risk = evaluation.setdefault("agent_summary", {}).setdefault("risk", {})
    details = risk.setdefault("details", {})
    checks = details.setdefault("checks", {})
    limits = overlay["limits"]
    checks["portfolio_position_ceiling"] = overlay["projected_position_pct"] <= limits["max_position_pct"]
    checks["portfolio_total_exposure"] = overlay["projected_total_exposure_pct"] <= limits["max_total_exposure_pct"]
    details["portfolio"] = overlay
    if request.side.strip().upper() == "SELL" and overlay["status"] == "PASS":
        blockers = evaluation.setdefault("blockers", [])
        blockers[:] = [blocker for blocker in blockers if blocker not in {"only_buy_side_supported", "quant_no_buy_signal"}]
        if not blockers:
            evaluation["decision"] = "READY_FOR_APPROVAL"
    if overlay["status"] != "PASS":
        risk["status"] = "REJECT"
        risk["reason"] = overlay["reason"]
        details["status"] = "REJECT"
        blockers = evaluation.setdefault("blockers", [])
        for blocker in overlay["blockers"]:
            if blocker not in blockers:
                blockers.append(blocker)
        if "risk_rejected" not in blockers:
            blockers.append("risk_rejected")
        evaluation["decision"] = "BLOCKED"
    evaluation["blocker_messages"] = blocker_messages_for_evaluation(evaluation)
    return evaluation


def blocker_messages_for_evaluation(evaluation: dict) -> list[dict]:
    agents = evaluation.get("agent_summary", {})
    quant = agents.get("quant", {})
    risk = agents.get("risk", {})
    portfolio = risk.get("details", {}).get("portfolio", {})
    portfolio_messages = portfolio.get("messages", {})
    messages = []
    for blocker in evaluation.get("blockers", []):
        message = portfolio_messages.get(blocker)
        if message is None and blocker == "quant_no_buy_signal":
            strategy = quant.get("strategy", {})
            gap = strategy.get("breakout_gap_pct")
            breakout_level = strategy.get("breakout_level")
            if gap is not None and breakout_level is not None:
                message = f"Quant signal is {quant.get('signal', 'NO_SIGNAL')} because price is {abs(float(gap)):.2f}% below breakout level {float(breakout_level):.2f}."
            else:
                message = f"Quant signal is {quant.get('signal', 'NO_SIGNAL')}; strategy conditions are not met."
        if message is None and blocker == "only_buy_side_supported":
            message = "This side is not supported by the current approval workflow."
        if message is None and blocker == "risk_rejected":
            message = risk.get("reason", "Risk engine rejected this order.")
        if message is None and blocker == "shariah_rejected":
            message = "Shariah agent rejected this symbol."
        if message is None:
            message = blocker
        messages.append({"blocker": blocker, "message": message})
    return messages


def evaluate_preview_request(request: PaperPreviewRequest) -> dict:
    evaluation = evaluate_candidate(
        symbol=request.symbol,
        side=request.side,
        quantity=request.quantity,
        price=request.price,
        position_pct=request.position_pct,
        total_exposure_pct=request.total_exposure_pct,
        loss_per_trade_pct=request.loss_per_trade_pct,
        daily_loss_pct=request.daily_loss_pct,
        orders_today=request.orders_today,
        **paper_test_overrides(request),
    )
    connection = db()
    try:
        return apply_portfolio_risk_overlay(connection, request, evaluation)
    finally:
        connection.close()


def quote_snapshot_for_preview(evaluation: dict, request: PaperPreviewRequest) -> dict:
    quant = evaluation.get("agent_summary", {}).get("quant", {})
    symbol = evaluation.get("symbol") or request.symbol.strip().upper()
    snapshot = {
        "symbol": symbol,
        "latest_close": quant.get("price") or evaluation.get("price"),
        "latest_date": quant.get("latest_date"),
        "source": quant.get("price_source"),
        "bars": quant.get("bars"),
        "min_bars": quant.get("min_bars"),
        "enough_history": quant.get("enough_history"),
        "data_freshness": quant.get("data_freshness"),
        "cache_cached_at": quant.get("cache_cached_at"),
        "cache_age_hours": quant.get("cache_age_hours"),
        "fallback_allowed": False,
        "stale_cache_allowed": True,
        "quote_snapshot_source": "quant_agent",
    }
    if snapshot["latest_date"] is not None and snapshot["source"] is not None:
        return snapshot

    try:
        market = summarize_history(
            symbol,
            days=14,
            min_bars=1,
            allow_fallback=False,
            allow_stale_cache=True,
        )
    except Exception as exc:
        snapshot["quote_snapshot_source"] = "market_data_error"
        snapshot["error"] = type(exc).__name__
        return snapshot

    snapshot.update(
        {
            "latest_close": market.get("latest_close"),
            "latest_date": market.get("latest_date"),
            "source": market.get("source"),
            "bars": market.get("bars"),
            "min_bars": market.get("min_bars"),
            "enough_history": market.get("enough_history"),
            "start_date": market.get("start_date"),
            "end_date": market.get("end_date"),
            "quote_snapshot_source": "market_data",
        }
    )
    return snapshot


@app.get("/")
def home() -> dict:
    settings = load_settings()
    broker_submission = broker_submission_configured(settings)
    return {
        "name": "Amanah Trader Local API",
        "status": "running",
        "routes": [
            "/health",
            "/system/mode",
            "/paper/status",
            "/moomoo/status",
            "/market-data/{symbol}",
            "/market-overview",
            "/stock/{symbol}/profile",
            "/investment-committee",
            "/watchlist",
            "/opportunities",
            "/opportunity-alerts",
            "/agent/evaluate",
            "/paper/preview",
            "/paper/approval",
            "/paper/execute/{queue_id}",
            "/paper/reconcile/{queue_id}",
            "/positions",
            "/portfolio",
            "/approvals",
            "/audit",
        ],
        "live_trading": False,
        "trading_mode": settings.trading_mode,
        "paper_execution_enabled": settings.paper_execution_enabled,
        "paper_execution_adapter": settings.paper_execution_adapter,
        "broker_submission": broker_submission,
    }


@app.get("/health")
def health() -> dict:
    settings = load_settings()
    return {
        "status": "ok",
        "mode": settings.moomoo_mode,
        "trading_mode": settings.trading_mode,
        "paper_execution_enabled": settings.paper_execution_enabled,
        "paper_execution_adapter": settings.paper_execution_adapter,
        "broker_submission": broker_submission_configured(settings),
    }


@app.get("/paper/status")
def paper_status() -> dict:
    settings = load_settings()
    return {
        "mode": "SIMULATE",
        "trading_mode": settings.trading_mode,
        "approval_required": settings.trading_mode == "approval",
        "paper_execution_enabled": settings.paper_execution_enabled,
        "paper_execution_adapter": settings.paper_execution_adapter,
        "live_trading": False,
        "broker_submission": broker_submission_configured(settings),
    }


@app.get("/system/mode")
def system_mode() -> dict:
    return trading_mode_status()


@app.get("/market-data/{symbol}")
def market_data_status(symbol: str) -> dict:
    return summarize_history(symbol, days=365, min_bars=200, allow_fallback=True)


@app.get("/market-overview")
def market_overview(stale_cache_hours: float = 24.0) -> dict:
    connection = db()
    try:
        return market_overview_snapshot(connection, stale_cache_hours=max(0.0, min(168.0, stale_cache_hours)))
    finally:
        connection.close()


@app.get("/stock/{symbol}/profile")
def stock_profile(symbol: str) -> dict:
    connection = db()
    try:
        return stock_profile_snapshot(connection, symbol)
    finally:
        connection.close()


@app.get("/investment-committee")
def investment_committee(limit: int = 50) -> dict:
    connection = db()
    try:
        return investment_committee_snapshot(connection, limit=limit)
    finally:
        connection.close()


@app.get("/positions")
def positions() -> dict:
    connection = db()
    try:
        return positions_snapshot(connection)
    finally:
        connection.close()


@app.get("/watchlist")
def watchlist() -> dict:
    connection = db()
    try:
        return get_watchlist_settings(connection)
    finally:
        connection.close()


@app.post("/watchlist")
def update_watchlist(request: WatchlistRequest) -> dict:
    connection = db()
    try:
        previous = get_watchlist_settings(connection)
        settings = save_watchlist_settings(
            connection,
            symbols=request.symbols,
            alert_threshold_pct=request.alert_threshold_pct,
        )
    finally:
        connection.close()
    changed = (
        previous["symbols"] != settings["symbols"]
        or previous["alert_threshold_pct"] != settings["alert_threshold_pct"]
    )
    if changed:
        add_audit_event(
            "watchlist_updated",
            {
                "symbols": settings["symbols"],
                "alert_threshold_pct": settings["alert_threshold_pct"],
            },
        )
    return settings


@app.get("/opportunities")
def opportunities(
    symbols: str | None = None,
    alert_threshold_pct: float | None = None,
    force: bool = False,
    min_scan_interval_minutes: int = DEFAULT_SCAN_THROTTLE_MINUTES,
) -> dict:
    connection = db()
    try:
        settings = get_watchlist_settings(connection)
        snapshot = latest_scan_snapshot(connection, symbols=settings["symbols"] if symbols is None else symbols.split(","))
    finally:
        connection.close()
    selected_symbols = symbols if symbols is not None else ",".join(settings["symbols"])
    selected_threshold = alert_threshold_pct if alert_threshold_pct is not None else settings["alert_threshold_pct"]
    throttle_minutes = max(0, min(120, min_scan_interval_minutes))
    if not force and throttle_minutes and snapshot is not None:
        last_scan_at = datetime.fromisoformat(snapshot["created_at"])
        if last_scan_at.tzinfo is None:
            last_scan_at = last_scan_at.replace(tzinfo=timezone.utc)
        seconds_since_scan = (datetime.now(timezone.utc) - last_scan_at).total_seconds()
        wait_seconds = max(0, int((throttle_minutes * 60) - seconds_since_scan))
        if wait_seconds > 0:
            return {
                "status": "THROTTLED",
                "throttled": True,
                "scan_id": None,
                "created_at": snapshot["created_at"],
                "last_scan_at": snapshot["created_at"],
                "wait_seconds": wait_seconds,
                "min_scan_interval_minutes": throttle_minutes,
                "alert_events": [],
                **snapshot,
            }
    scan = scan_opportunities(selected_symbols, alert_threshold_pct=selected_threshold)
    audit = add_audit_event(
        "opportunity_scan",
        {
            "count": scan["count"],
            "ready_count": scan["ready_count"],
            "alert_count": scan["alert_count"],
            "alert_threshold_pct": selected_threshold,
            "symbols": [item["symbol"] for item in scan["items"]],
        },
    )
    connection = db()
    try:
        alert_events = save_opportunity_scan(
            connection,
            scan_id=audit["id"],
            scanned_at=audit["created_at"],
            scan=scan,
        )
    finally:
        connection.close()
    return {"status": "SCANNED", "throttled": False, "scan_id": audit["id"], "created_at": audit["created_at"], "alert_events": alert_events, **scan}


@app.get("/opportunity-alerts")
def opportunity_alerts(limit: int = 50) -> list[dict]:
    connection = db()
    try:
        return list_alert_events(connection, limit=max(1, min(200, limit)))
    finally:
        connection.close()


@app.get("/moomoo/status")
def moomoo_status() -> dict:
    return check_moomoo_status()


@app.post("/agent/evaluate")
def evaluate_agents(request: PaperPreviewRequest) -> dict:
    evaluation = evaluate_preview_request(request)
    audit = add_audit_event("agent_evaluation", evaluation)
    return {"evaluation_id": audit["id"], "created_at": audit["created_at"], "broker_submission": False, "evaluation": evaluation}


@app.post("/paper/preview")
def preview_paper_order(request: PaperPreviewRequest) -> dict:
    evaluation = evaluate_preview_request(request)
    quote_snapshot = quote_snapshot_for_preview(evaluation, request)
    side = request.side.strip().upper()
    if evaluation["decision"] != "READY_FOR_APPROVAL" or evaluation["price"] is None:
        preview = {
            "status": "REJECT",
            "reason": "agent_evaluation_blocked",
            "blockers": evaluation["blockers"],
            "symbol": evaluation["symbol"],
            "quantity": evaluation["quantity"],
            "price": evaluation["price"],
            "notional": evaluation["notional"],
            "side": side,
            "broker_submission": False,
            "quote_snapshot": quote_snapshot,
            "blocker_messages": evaluation.get("blocker_messages", []),
            "agent_summary": evaluation["agent_summary"],
        }
    else:
        preview = {
            "status": "READY_FOR_APPROVAL",
            "execution": "PAPER_ONLY",
            "broker_submission": False,
            "symbol": evaluation["symbol"],
            "side": side,
            "quantity": evaluation["quantity"],
            "price": evaluation["price"],
            "notional": evaluation["notional"],
            "blockers": evaluation.get("blockers", []),
            "quote_snapshot": quote_snapshot,
            "shariah": evaluation["agent_summary"]["shariah"],
            "risk": evaluation["agent_summary"]["risk"],
            "blocker_messages": evaluation.get("blocker_messages", []),
            "agent_summary": evaluation["agent_summary"],
        }

    audit = add_audit_event("paper_preview", preview)
    return {"preview_id": audit["id"], "created_at": audit["created_at"], "broker_submission": False, "preview": preview}


@app.post("/paper/approval")
def approve_paper_order(request: PaperApprovalRequest) -> dict:
    settings = load_settings()
    preview = request.preview
    shariah = preview.get("agent_summary", {}).get("shariah", preview.get("shariah", {}))
    risk = preview.get("agent_summary", {}).get("risk", preview.get("risk", {}))
    side = preview.get("side", "BUY")
    candidate = {
        "signal": str(side).upper() if preview.get("status") == "READY_FOR_APPROVAL" else "HOLD",
        "compliance": {
            "status": "COMPLIANT" if shariah.get("status") == "PASS" else "REJECT",
            "source": shariah.get("provider", "SHARIAH_AGENT"),
        },
        "symbol": preview.get("symbol"),
        "side": side,
        "quantity": preview.get("quantity"),
        "price": preview.get("price"),
        "notional": preview.get("notional"),
    }
    if preview.get("status") != "READY_FOR_APPROVAL":
        approval = {"status": "REJECT", "reason": "preview_not_ready_for_approval", "broker_submission": False}
    elif risk.get("status") != "PASS":
        approval = {"status": "REJECT", "reason": "risk_gate_failed", "broker_submission": False}
    else:
        approval = approve_candidate(candidate, approved_by_user=request.approved)
    approval["broker_submission"] = False
    approval["paper_execution_enabled"] = settings.paper_execution_enabled
    connection = db()
    try:
        queue_item = record_approval(connection, preview=preview, approval=approval, approved_by_user=request.approved)
    finally:
        connection.close()
    payload = {"approved_by_user": request.approved, "approval": approval, "preview": preview}
    audit = add_audit_event("paper_approval", payload)
    return {"approval_id": audit["id"], "queue_id": queue_item["id"], "created_at": audit["created_at"], "broker_submission": False, "approval": approval}


@app.post("/audit")
def record_audit(event_type: str, payload: str) -> dict:
    return add_audit_event(event_type, {"payload": payload})


@app.get("/audit")
def list_audit() -> list[dict]:
    connection = db()
    try:
        rows = connection.execute("SELECT id, created_at, event_type, payload FROM audit_events ORDER BY id DESC LIMIT 100").fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


@app.get("/approvals")
def approvals() -> list[dict]:
    connection = db()
    try:
        return list_approvals(connection)
    finally:
        connection.close()


@app.post("/paper/execute/{queue_id}")
def execute_paper(queue_id: int, request: PaperExecutionRequest | None = None) -> dict:
    if request is None or request.confirmation_phrase != PAPER_EXECUTION_CONFIRMATION:
        result = {
            "status": "CONFIRMATION_REQUIRED",
            "queue_id": queue_id,
            "message": "confirmation_phrase must exactly equal EXECUTE PAPER",
            "required_confirmation": PAPER_EXECUTION_CONFIRMATION,
            "broker_submission": False,
        }
        audit = add_audit_event("paper_execution_rejected", result)
        return {"execution_id": audit["id"], "created_at": audit["created_at"], **result}

    connection = db()
    try:
        result = execute_paper_order(connection, queue_id)
    finally:
        connection.close()
    audit = add_audit_event("paper_execution", result)
    return {"execution_id": audit["id"], "created_at": audit["created_at"], **result}


@app.post("/paper/reconcile/{queue_id}")
def reconcile_paper(queue_id: int) -> dict:
    connection = db()
    try:
        result = reconcile_submitted_paper_order(connection, queue_id)
        portfolio_sync = None
        if result.get("status") == "BROKER_FILLED":
            approval = get_approval(connection, queue_id)
            if approval is not None:
                portfolio_sync = sync_filled_order(connection, approval)
    finally:
        connection.close()
    payload = {**result, "portfolio_sync": portfolio_sync}
    audit = add_audit_event("paper_reconciliation", payload)
    return {"reconciliation_id": audit["id"], "created_at": audit["created_at"], **payload}


@app.get("/portfolio")
def portfolio() -> dict:
    connection = db()
    try:
        return portfolio_snapshot_with_exposure(connection)
    finally:
        connection.close()
