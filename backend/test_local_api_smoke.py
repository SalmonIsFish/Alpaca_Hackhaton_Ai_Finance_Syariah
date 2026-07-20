"""Smoke-test the local FastAPI contract without submitting orders."""

from fastapi.testclient import TestClient

from local_api import app


def main() -> None:
    client = TestClient(app)

    home = client.get("/")
    assert home.status_code == 200, home.text
    home_payload = home.json()
    assert home_payload["live_trading"] is False
    assert "/health" in home_payload["routes"]
    assert "/paper/status" in home_payload["routes"]

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

    print("PASS: local API smoke contract is safe for dashboard use.")


if __name__ == "__main__":
    main()
