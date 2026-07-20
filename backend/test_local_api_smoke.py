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
                    "ticker": "0001",
                    "issuer_name": "Test Issuer",
                    "shariah_status": "COMPLIANT",
                }
            ],
        }
    ),
    encoding="utf-8",
)
os.environ["SHARIAH_UNIVERSE_PATH"] = str(universe_path)

from agent_coordinator import evaluate_candidate
from agents.shariah_agent import detect_market
import local_api
from local_api import app


def main() -> None:
    client = TestClient(app)

    home = client.get("/")
    assert home.status_code == 200, home.text
    home_payload = home.json()
    assert home_payload["live_trading"] is False
    assert "/health" in home_payload["routes"]
    assert "/paper/status" in home_payload["routes"]
    assert "/market-data/{symbol}" in home_payload["routes"]
    assert "/agent/evaluate" in home_payload["routes"]
    assert "/paper/preview" in home_payload["routes"]
    assert "/paper/approval" in home_payload["routes"]
    assert "/approvals" in home_payload["routes"]

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
    assert detect_market("0001") == "MY"
    assert detect_market("AAPL") == "US"

    market_data = client.get("/market-data/TEST")
    assert market_data.status_code == 200, market_data.text
    market_payload = market_data.json()
    assert market_payload["symbol"] == "TEST"
    assert market_payload["source"] in {"fixture", "fixture_after_tiingo_error"}
    assert market_payload["bars"] == 2
    assert market_payload["enough_history"] is False

    agent_evaluation = client.post(
        "/agent/evaluate",
        json={
            "symbol": "0001",
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
    assert agent_evaluation.status_code == 200, agent_evaluation.text
    evaluation_payload = agent_evaluation.json()
    assert evaluation_payload["broker_submission"] is False
    evaluation = evaluation_payload["evaluation"]
    assert set(evaluation["agent_summary"]) == {"shariah", "quant", "risk"}
    assert evaluation["agent_summary"]["shariah"]["market"] == "MY"
    assert evaluation["agent_summary"]["shariah"]["provider"] == "SC_MY_LOCAL_UNIVERSE"
    assert evaluation["agent_summary"]["shariah"]["status"] == "PASS"
    assert evaluation["agent_summary"]["risk"]["status"] == "PASS"
    assert evaluation["agent_summary"]["quant"]["signal"] == "NO_SIGNAL"
    assert evaluation["decision"] == "BLOCKED"
    assert "quant_no_buy_signal" in evaluation["blockers"]

    ready_candidate = evaluate_candidate(
        symbol="0001",
        side="BUY",
        quantity=2,
        price=50.0,
        position_pct=1.0,
        total_exposure_pct=5.0,
        loss_per_trade_pct=0.2,
        daily_loss_pct=0.3,
        orders_today=0,
        quant_override={
            "agent": "quant",
            "status": "PASS",
            "symbol": "0001",
            "signal": "BUY",
            "reason": "test_override",
            "price": 50.0,
            "bars": 200,
            "price_source": "test",
            "strategy": {"signal": "BUY"},
        },
    )
    assert ready_candidate["decision"] == "READY_FOR_APPROVAL"
    assert ready_candidate["broker_submission"] is False
    assert ready_candidate["agent_summary"]["shariah"]["status"] == "PASS"
    assert ready_candidate["agent_summary"]["risk"]["status"] == "PASS"

    original_evaluate_candidate = local_api.evaluate_candidate
    local_api.evaluate_candidate = lambda **kwargs: {
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": 1,
        "price": 333.74,
        "notional": 333.74,
        "decision": "READY_FOR_APPROVAL",
        "blockers": [],
        "broker_submission": False,
        "agent_summary": {
            "shariah": {
                "agent": "shariah",
                "market": "US",
                "provider": "ZOYA",
                "status": "PASS",
                "symbol": "AAPL",
                "reason": "COMPLIANT",
                "details": {"status": "COMPLIANT", "symbol": "AAPL"},
            },
            "quant": {
                "agent": "quant",
                "status": "PASS",
                "symbol": "AAPL",
                "signal": "BUY",
                "reason": "test_override",
                "price": 333.74,
                "bars": 218,
                "price_source": "tiingo",
                "strategy": {"signal": "BUY"},
            },
            "risk": {
                "agent": "risk_engine",
                "status": "PASS",
                "reason": "risk_limits_passed",
                "details": {"status": "PASS", "checks": {}},
            },
        },
    }
    try:
        ready_preview = client.post(
            "/paper/preview",
            json={
                "symbol": "AAPL",
                "side": "BUY",
                "quantity": 1,
                "price": 333.74,
                "position_pct": 1.0,
                "total_exposure_pct": 5.0,
                "loss_per_trade_pct": 0.2,
                "daily_loss_pct": 0.3,
                "orders_today": 0,
            },
        )
    finally:
        local_api.evaluate_candidate = original_evaluate_candidate
    assert ready_preview.status_code == 200, ready_preview.text
    ready_preview_payload = ready_preview.json()
    assert ready_preview_payload["broker_submission"] is False
    assert ready_preview_payload["preview"]["status"] == "READY_FOR_APPROVAL"
    assert ready_preview_payload["preview"]["broker_submission"] is False
    assert ready_preview_payload["preview"]["agent_summary"]["shariah"]["provider"] == "ZOYA"

    ready_approval = client.post(
        "/paper/approval",
        json={"preview": ready_preview_payload["preview"], "approved": True},
    )
    assert ready_approval.status_code == 200, ready_approval.text
    ready_approval_payload = ready_approval.json()
    assert ready_approval_payload["broker_submission"] is False
    assert ready_approval_payload["queue_id"] > 0
    assert ready_approval_payload["approval"]["status"] == "APPROVED_PAPER_READY"
    assert ready_approval_payload["approval"]["broker_submission"] is False

    approvals = client.get("/approvals")
    assert approvals.status_code == 200, approvals.text
    approvals_payload = approvals.json()
    assert approvals_payload
    latest_approval = approvals_payload[0]
    assert latest_approval["symbol"] == "AAPL"
    assert latest_approval["side"] == "BUY"
    assert latest_approval["approval_status"] == "APPROVED_PAPER_READY"
    assert latest_approval["execution_environment"] == "SIMULATE"
    assert latest_approval["broker_submission"] is False
    assert latest_approval["shariah_status"] == "PASS"
    assert latest_approval["shariah_market"] == "US"
    assert latest_approval["quant_signal"] == "BUY"
    assert latest_approval["risk_status"] == "PASS"

    preview = client.post(
        "/paper/preview",
        json={
            "symbol": "0001",
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
    assert preview_payload["preview"]["status"] == "REJECT"
    assert preview_payload["preview"]["broker_submission"] is False
    assert preview_payload["preview"]["agent_summary"]["shariah"]["status"] == "PASS"
    assert preview_payload["preview"]["agent_summary"]["risk"]["status"] == "PASS"
    assert "quant_no_buy_signal" in preview_payload["preview"]["blockers"]

    approval = client.post(
        "/paper/approval",
        json={"preview": preview_payload["preview"], "approved": True},
    )
    assert approval.status_code == 200, approval.text
    approval_payload = approval.json()
    assert approval_payload["broker_submission"] is False
    assert approval_payload["queue_id"] > 0
    assert approval_payload["approval"]["broker_submission"] is False
    assert approval_payload["approval"]["status"] == "REJECT"

    print("PASS: local API smoke contract is safe for dashboard use.")


if __name__ == "__main__":
    main()
