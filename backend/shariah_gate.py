"""Fail-closed Shariah universe gate."""

import json
from pathlib import Path

from config import load_settings


def check_symbol(symbol: str) -> dict:
    settings = load_settings()
    if not settings.shariah_universe_path:
        return {"status": "REJECT", "reason": "universe_not_configured"}

    path = Path(settings.shariah_universe_path)
    if not path.exists():
        return {"status": "REJECT", "reason": "universe_file_missing"}

    dataset = json.loads(path.read_text(encoding="utf-8-sig"))
    validation = dataset.get("validation", {})
    if validation.get("status") != "active":
        return {"status": "REJECT", "reason": "universe_not_active", "dataset_status": validation.get("status")}

    record = next((item for item in dataset.get("records", []) if str(item.get("ticker")) == symbol), None)
    if not record:
        return {"status": "REJECT", "reason": "symbol_not_in_universe"}
    if record.get("shariah_status") != "COMPLIANT":
        return {"status": "REJECT", "reason": "symbol_not_compliant"}
    return {"status": "PASS", "reason": "symbol_compliant", "issuer_name": record.get("issuer_name")}
