"""Minimal local API for the paper-trading dashboard."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent_coordinator import evaluate_candidate
from approval_queue import ensure_approval_queue, list_approvals, record_approval
from approval_workflow import approve_candidate
from config import load_settings
from market_data import summarize_history
from moomoo_status import check_moomoo_status
from opportunity_scanner import scan_opportunities
from paper_execution import execute_paper_order
from trading_modes import trading_mode_status
from watchlist_store import (
    ensure_watchlist_tables,
    get_watchlist_settings,
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


def evaluate_preview_request(request: PaperPreviewRequest) -> dict:
    return evaluate_candidate(
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
            "/watchlist",
            "/opportunities",
            "/opportunity-alerts",
            "/agent/evaluate",
            "/paper/preview",
            "/paper/approval",
            "/paper/execute/{queue_id}",
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
            "shariah": evaluation["agent_summary"]["shariah"],
            "risk": evaluation["agent_summary"]["risk"],
            "agent_summary": evaluation["agent_summary"],
        }

    audit = add_audit_event("paper_preview", preview)
    return {"preview_id": audit["id"], "created_at": audit["created_at"], "broker_submission": False, "preview": preview}


@app.post("/paper/approval")
def approve_paper_order(request: PaperApprovalRequest) -> dict:
    settings = load_settings()
    preview = request.preview
    shariah = preview.get("agent_summary", {}).get("shariah", preview.get("shariah", {}))
    candidate = {
        "signal": "BUY" if preview.get("status") == "READY_FOR_APPROVAL" else "HOLD",
        "compliance": {
            "status": "COMPLIANT" if shariah.get("status") == "PASS" else "REJECT",
            "source": shariah.get("provider", "SHARIAH_AGENT"),
        },
        "symbol": preview.get("symbol"),
        "side": preview.get("side", "BUY"),
        "quantity": preview.get("quantity"),
        "price": preview.get("price"),
        "notional": preview.get("notional"),
    }
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
