"""Minimal local API for the paper-trading dashboard."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import load_settings


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
    connection.commit()
    return connection


@app.get("/")
def home() -> dict:
    return {
        "name": "Amanah Trader Local API",
        "status": "running",
        "routes": ["/health", "/paper/status", "/audit"],
        "live_trading": False,
    }


@app.get("/health")
def health() -> dict:
    settings = load_settings()
    return {"status": "ok", "mode": settings.moomoo_mode, "broker_submission": False}


@app.get("/paper/status")
def paper_status() -> dict:
    return {"mode": "SIMULATE", "approval_required": True, "live_trading": False, "broker_submission": False}


@app.post("/audit")
def record_audit(event_type: str, payload: str) -> dict:
    created_at = datetime.now(timezone.utc).isoformat()
    connection = db()
    try:
        cursor = connection.execute("INSERT INTO audit_events (created_at, event_type, payload) VALUES (?, ?, ?)", (created_at, event_type, payload))
        connection.commit()
        return {"id": cursor.lastrowid, "created_at": created_at, "event_type": event_type}
    finally:
        connection.close()


@app.get("/audit")
def list_audit() -> list[dict]:
    connection = db()
    try:
        rows = connection.execute("SELECT id, created_at, event_type, payload FROM audit_events ORDER BY id DESC LIMIT 100").fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()
