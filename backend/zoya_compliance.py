"""Read-only Zoya Shariah-compliance adapter."""

import json
from urllib.request import Request, urlopen

from config import load_settings


QUERY = """
query GetReport($symbol: String!) {
  basicCompliance {
    report(symbol: $symbol) {
      symbol
      name
      exchange
      status
      reportDate
    }
  }
}
"""


def check_us_symbol(symbol: str) -> dict:
    settings = load_settings()
    if not settings.zoya_api_key:
        return {"status": "NOT_CONFIGURED", "reason": "zoya_api_key_missing"}
    if settings.zoya_environment not in {"sandbox", "live"}:
        return {"status": "REJECT", "reason": "invalid_zoya_environment"}

    endpoint = f"https://{settings.zoya_environment}-api.zoya.finance/graphql"
    prefix = f"{settings.zoya_environment}-"
    auth = settings.zoya_api_key if settings.zoya_api_key.startswith(prefix) else prefix + settings.zoya_api_key
    body = json.dumps({"query": QUERY, "variables": {"symbol": symbol}}).encode("utf-8")
    request = Request(endpoint, data=body, headers={"Content-Type": "application/json", "Authorization": auth})
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"status": "ERROR", "reason": type(exc).__name__}
    if payload.get("errors"):
        return {"status": "ERROR", "reason": "zoya_api_error"}

    report = ((payload.get("data") or {}).get("basicCompliance") or {}).get("report")
    if not report:
        return {"status": "REJECT", "reason": "no_report", "symbol": symbol}
    return {"status": report.get("status", "UNKNOWN"), "symbol": report.get("symbol"), "exchange": report.get("exchange"), "report_date": report.get("reportDate")}
