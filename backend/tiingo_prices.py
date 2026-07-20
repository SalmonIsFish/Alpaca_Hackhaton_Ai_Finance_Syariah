"""Read-only Tiingo EOD adapter with an explicit fixture fallback."""

from __future__ import annotations

import json
from datetime import date, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from config import load_settings


def _fixture_prices(symbol: str) -> list[dict]:
    today = date.today()
    return [
        {"symbol": symbol, "date": (today - timedelta(days=2)).isoformat(), "open": 100.0, "high": 102.0, "low": 99.0, "close": 101.0, "volume": 100000},
        {"symbol": symbol, "date": (today - timedelta(days=1)).isoformat(), "open": 101.0, "high": 103.0, "low": 100.0, "close": 102.0, "volume": 110000},
    ]


def fetch_eod_prices(symbol: str, start_date: str, end_date: str, *, allow_fallback: bool = True) -> tuple[list[dict], str]:
    """Return normalized bars and their source (tiingo or fixture)."""
    settings = load_settings()
    if not settings.tiingo_api_token:
        if allow_fallback:
            return _fixture_prices(symbol), "fixture"
        raise RuntimeError("TIINGO_API_TOKEN is not configured")

    query = urlencode({"startDate": start_date, "endDate": end_date})
    url = f"https://api.tiingo.com/tiingo/daily/{symbol}/prices?{query}"
    request = Request(url, headers={"Content-Type": "application/json", "Authorization": f"Token {settings.tiingo_api_token}"})
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        if allow_fallback:
            return _fixture_prices(symbol), "fixture_after_tiingo_error"
        raise

    bars = [
        {"symbol": symbol, "date": row["date"][:10], "open": row["open"], "high": row["high"], "low": row["low"], "close": row["close"], "volume": row["volume"]}
        for row in payload
    ]
    return bars, "tiingo"
