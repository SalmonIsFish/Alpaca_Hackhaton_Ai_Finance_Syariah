"""Test-only US pipeline; no external API call and no order submission."""

from us_strategy import evaluate_us_s001


bars = [
    {"date": f"2026-01-{(index % 28) + 1:02d}", "close": 100.0 + index, "open": 99.0 + index, "high": 101.0 + index, "low": 98.0 + index, "volume": 100000}
    for index in range(200)
]
result = evaluate_us_s001(
    "TEST_ONLY",
    bars,
    compliance_override={"status": "COMPLIANT", "symbol": "TEST_ONLY", "exchange": "TEST", "source": "LOCAL_TEST_FIXTURE"},
)
print(result)
print("TEST ONLY: no Zoya call and no order submission.")
