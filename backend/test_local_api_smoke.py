"""Smoke-test the local FastAPI contract without submitting orders."""

import json
import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient


fixture_dir = tempfile.TemporaryDirectory()
universe_path = Path(fixture_dir.name) / "shariah_universe.json"
universe_path.write_text(
    json.dumps(
        {
            "validation": {"status": "active"},
            "records": [
                {
                    "ticker": "TEST",
                    "issuer_name": "Test Issuer",
                    "shariah_status": "COMPLIANT",
                }
            ],
        }
    ),
    encoding="utf-8",
)
os.environ["SHARIAH_UNIVERSE_PATH"] = str(universe_path)

from local_api import app


def main() -> None:
    client = TestClient(app)

    home = client.get("/")
    assert home.status_code == 200, home.text
    home_payload = home.json()
    assert home_payload["live_trading"] is False
    assert "/health" in home_payload["routes"]
    assert "/paper/status" in home_payload["routes"]
    assert "/paper/preview" in home_payload["routes"]
    assert "/paper/approval" in home_payload["routes"]

    health = client.get("/health")
    assert health.status_code == 200, health.text
    health_payload = health.json()
    assert health_payload["status"] == "ok"
    assert health_payload["mode"] == "paper"
    assert health_payload["broker_submission"] is False

    paper_status = client.get("/paper/status")
    assert paper_status.status_code == 200, paper_status.text
    paper_payload = paper_status.json()
    assert paper_payload["mode"] == "SIMULATE"
    assert paper_payload["approval_required"] is True
    assert paper_payload["live_trading"] is False
    assert paper_payload["broker_submission"] is False

    preview = client.post(
        "/paper/preview",
        json={
            "symbol": "TEST",
            "side": "BUY",
            "quantity": 2,
            "price": 50.0,
            "position_pct": 1.0,
            "total_exposure_pct": 5.0,
            "loss_per_trade_pct": 0.2,
            "daily_loss_pct": 0.3,
            "orders_today": 0,
        },
    )
    assert preview.status_code == 200, preview.text
    preview_payload = preview.json()
    assert preview_payload["broker_submission"] is False
    assert preview_payload["preview"]["status"] == "READY_FOR_APPROVAL"
    assert preview_payload["preview"]["broker_submission"] is False
    assert preview_payload["preview"]["shariah"]["status"] == "PASS"
    assert preview_payload["preview"]["risk"]["status"] == "PASS"

    approval = client.post(
        "/paper/approval",
        json={"preview": preview_payload["preview"], "approved": True},
    )
    assert approval.status_code == 200, approval.text
    approval_payload = approval.json()
    assert approval_payload["broker_submission"] is False
    assert approval_payload["approval"]["broker_submission"] is False
    assert approval_payload["approval"]["status"] == "APPROVED_PAPER_READY"

    print("PASS: local API smoke contract is safe for dashboard use.")


if __name__ == "__main__":
    main()
