"""Minimal local API for the paper-trading dashboard."""

import sqlite3
import json
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
    connection.commit()
    return connection


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


class PaperApprovalRequest(BaseModel):
    preview: dict
    approved: bool


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


@app.get("/")
def home() -> dict:
    return {
        "name": "Amanah Trader Local API",
        "status": "running",
        "routes": ["/health", "/paper/status", "/market-data/{symbol}", "/agent/evaluate", "/paper/preview", "/paper/approval", "/approvals", "/audit"],
        "live_trading": False,
    }


@app.get("/health")
def health() -> dict:
    settings = load_settings()
    return {"status": "ok", "mode": settings.moomoo_mode, "broker_submission": False}


@app.get("/paper/status")
def paper_status() -> dict:
    return {"mode": "SIMULATE", "approval_required": True, "live_trading": False, "broker_submission": False}


@app.get("/market-data/{symbol}")
def market_data_status(symbol: str) -> dict:
    return summarize_history(symbol, days=365, min_bars=200, allow_fallback=True)


@app.post("/agent/evaluate")
def evaluate_agents(request: PaperPreviewRequest) -> dict:
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
    )
    audit = add_audit_event("agent_evaluation", evaluation)
    return {"evaluation_id": audit["id"], "created_at": audit["created_at"], "broker_submission": False, "evaluation": evaluation}


@app.post("/paper/preview")
def preview_paper_order(request: PaperPreviewRequest) -> dict:
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
    )
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
