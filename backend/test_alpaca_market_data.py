"""Verify the Alpaca market-data adapter without contacting Alpaca."""

import os

import alpaca_market_data


BAR_PAGE_1 = {
    "symbol": "AAPL",
    "bars": [
        {"t": "2026-08-06T04:00:00Z", "o": 309.0, "h": 312.0, "l": 308.5, "c": 311.0, "v": 30000000, "n": 700000, "vw": 310.1},
        {"t": "2026-08-07T04:00:00Z", "o": 311.45, "h": 314.81, "l": 310.74, "c": 313.33, "v": 34646756, "n": 718830, "vw": 312.93},
    ],
    "next_page_token": "PAGE2",
}

BAR_PAGE_2 = {
    "symbol": "AAPL",
    "bars": [
        {"t": "2026-08-10T04:00:00Z", "o": 313.5, "h": 316.0, "l": 312.9, "c": 315.2, "v": 28000000, "n": 640000, "vw": 314.4},
    ],
    "next_page_token": None,
}

CONTRACTS = {
    "option_contracts": [
        {
            "id": "ce20dae1", "symbol": "AAPL260918C00350000", "name": "AAPL Sep 18 2026 350 Call",
            "status": "active", "tradable": True, "expiration_date": "2026-09-18", "root_symbol": "AAPL",
            "underlying_symbol": "AAPL", "type": "call", "style": "american",
            "strike_price": "350", "multiplier": "100", "size": "100",
        },
        {
            "id": "aa11bb22", "symbol": "AAPL260918P00300000", "name": "AAPL Sep 18 2026 300 Put",
            "status": "active", "tradable": True, "expiration_date": "2026-09-18", "root_symbol": "AAPL",
            "underlying_symbol": "AAPL", "type": "put", "style": "american",
            "strike_price": "300", "multiplier": "100", "size": "100",
        },
    ],
    "next_page_token": None,
}

SNAPSHOTS = {
    "snapshots": {
        "AAPL260918C00350000": {
            "latestQuote": {"ap": 5.10, "as": 48, "bp": 4.60, "bs": 50, "t": "2026-08-18T14:00:25Z"},
            "latestTrade": {"p": 4.85, "s": 1, "t": "2026-08-18T13:44:29Z"},
            "dailyBar": {"c": 4.90, "h": 5.2, "l": 4.5, "o": 4.7, "v": 1200},
        },
        "AAPL260918P00300000": {
            "latestQuote": {"ap": 3.30, "as": 20, "bp": 2.90, "bs": 25, "t": "2026-08-18T14:00:25Z"},
            "latestTrade": {"p": 3.05, "s": 2, "t": "2026-08-18T13:40:00Z"},
            "dailyBar": {"c": 3.10, "h": 3.4, "l": 2.8, "o": 3.0, "v": 800},
        },
    },
    "next_page_token": None,
}


class FakeData:
    """Replays canned Alpaca data-API responses and records every request."""

    def __init__(self, responses=None, *, fail=False, status_code=500):
        self.calls = []
        self.responses = responses or {}
        self.fail = fail
        self.status_code = status_code

    def __call__(self, path, params, *, credentials, base_url=None):
        self.calls.append({"path": path, "params": dict(params), "base_url": base_url, "credentials": credentials})
        if self.fail:
            return {"ok": False, "status_code": self.status_code, "data": {"message": "boom"}, "reason": f"http_{self.status_code}"}
        token = params.get("page_token")
        for prefix, payload in self.responses.items():
            if path.startswith(prefix):
                if isinstance(payload, dict) and "__pages__" in payload:
                    return {"ok": True, "status_code": 200, "data": payload["__pages__"][token]}
                return {"ok": True, "status_code": 200, "data": payload}
        raise AssertionError(f"unexpected data request {path}")


def check_bar_normalization_and_paging() -> None:
    data = FakeData({"/v2/stocks/AAPL/bars": {"__pages__": {None: BAR_PAGE_1, "PAGE2": BAR_PAGE_2}}})
    alpaca_market_data.alpaca_data_request = data

    bars, source = alpaca_market_data.fetch_eod_prices("aapl", "2026-08-01", "2026-08-11")
    assert source == "alpaca", source
    assert len(bars) == 3, "both pages must be concatenated"
    assert bars[0] == {
        "symbol": "AAPL",
        "date": "2026-08-06",
        "open": 309.0,
        "high": 312.0,
        "low": 308.5,
        "close": 311.0,
        "volume": 30000000,
    }
    assert bars[-1]["date"] == "2026-08-10"
    assert bars[-1]["close"] == 315.2

    first = data.calls[0]
    assert first["path"] == "/v2/stocks/AAPL/bars"
    assert first["params"]["timeframe"] == "1Day"
    assert first["params"]["start"] == "2026-08-01"
    assert first["params"]["end"] == "2026-08-11"
    assert first["params"]["adjustment"] == "all", "splits/dividends must be adjusted for SMA math"
    assert "page_token" not in first["params"]
    assert data.calls[1]["params"]["page_token"] == "PAGE2"
    assert len(data.calls) == 2, "paging must stop once next_page_token is null"


def check_fallback_and_cache_paths() -> None:
    original_read = alpaca_market_data.read_market_cache
    original_write = alpaca_market_data.write_market_cache
    alpaca_market_data.write_market_cache = lambda *a, **k: None
    try:
        # No credentials at all.
        os.environ.pop("ALPACA_API_KEY_ID", None)
        alpaca_market_data.alpaca_data_request = FakeData()
        alpaca_market_data.read_market_cache = lambda symbol: []
        bars, source = alpaca_market_data.fetch_eod_prices("AAPL", "2026-08-01", "2026-08-11")
        assert source == "fixture", source
        assert bars, "fixture fallback must return bars"

        cached = [{"symbol": "AAPL", "date": "2026-08-05", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 10}]
        alpaca_market_data.read_market_cache = lambda symbol: cached
        bars, source = alpaca_market_data.fetch_eod_prices("AAPL", "2026-08-01", "2026-08-11", allow_stale_cache=True)
        assert source == "alpaca_cache_no_credentials", source
        assert bars == cached

        raised = False
        try:
            alpaca_market_data.fetch_eod_prices("AAPL", "2026-08-01", "2026-08-11", allow_fallback=False)
        except alpaca_market_data.AlpacaDataError as exc:
            raised = True
            assert exc.error_code == "missing_credentials", exc.error_code
        assert raised, "allow_fallback=False must raise instead of returning fixtures"

        os.environ["ALPACA_API_KEY_ID"] = "TEST-KEY-ID"

        # Credentials present but the request fails.
        alpaca_market_data.alpaca_data_request = FakeData(fail=True)
        alpaca_market_data.read_market_cache = lambda symbol: []
        bars, source = alpaca_market_data.fetch_eod_prices("AAPL", "2026-08-01", "2026-08-11")
        assert source == "fixture_after_alpaca_error", source

        alpaca_market_data.read_market_cache = lambda symbol: cached
        bars, source = alpaca_market_data.fetch_eod_prices("AAPL", "2026-08-01", "2026-08-11", allow_stale_cache=True)
        assert source == "alpaca_cache_after_error", source

        raised = False
        try:
            alpaca_market_data.fetch_eod_prices("AAPL", "2026-08-01", "2026-08-11", allow_fallback=False)
        except alpaca_market_data.AlpacaDataError as exc:
            raised = True
            assert exc.status_code == 500, exc.status_code
        assert raised
    finally:
        alpaca_market_data.read_market_cache = original_read
        alpaca_market_data.write_market_cache = original_write


def check_sip_fallback_to_iex() -> None:
    """The Basic plan cannot query recent SIP data; drop to IEX, never to fixtures."""

    class SipDenied:
        def __init__(self):
            self.calls = []

        def __call__(self, path, params, *, credentials, base_url=None):
            self.calls.append(dict(params))
            if params.get("feed") == "iex":
                return {"ok": True, "status_code": 200, "data": BAR_PAGE_2}
            return {
                "ok": False,
                "status_code": 403,
                "data": {"message": "subscription does not permit querying recent SIP data"},
                "reason": "http_403",
            }

    denied = SipDenied()
    alpaca_market_data.alpaca_data_request = denied
    bars, source = alpaca_market_data.fetch_eod_prices("AAPL", "2026-08-01", "2026-08-18")
    assert source == "alpaca_iex", source
    assert len(bars) == 1 and bars[0]["close"] == 315.2
    assert "feed" not in denied.calls[0] or denied.calls[0].get("feed") is None
    assert denied.calls[1]["feed"] == "iex"

    # An explicit feed choice is honoured rather than silently overridden.
    os.environ["ALPACA_DATA_FEED"] = "sip"
    try:
        pinned = SipDenied()
        alpaca_market_data.alpaca_data_request = pinned
        bars, source = alpaca_market_data.fetch_eod_prices("AAPL", "2026-08-01", "2026-08-18")
        assert source == "fixture_after_alpaca_error", source
        assert len(pinned.calls) == 1, "an explicit feed must not trigger the IEX retry"
    finally:
        os.environ.pop("ALPACA_DATA_FEED", None)

    # A non-subscription error still falls back normally.
    alpaca_market_data.alpaca_data_request = FakeData(fail=True, status_code=500)
    bars, source = alpaca_market_data.fetch_eod_prices("AAPL", "2026-08-01", "2026-08-18")
    assert source == "fixture_after_alpaca_error", source


def check_transient_network_retry() -> None:
    """A transport blip must be retried, not turned into a fixture."""

    class Flaky:
        def __init__(self):
            self.attempts = 0

        def __call__(self, path, params, *, credentials, base_url=None):
            self.attempts += 1
            if self.attempts == 1:
                return {"ok": False, "status_code": 0, "data": {}, "reason": "URLError"}
            return {"ok": True, "status_code": 200, "data": BAR_PAGE_2}

    flaky = Flaky()
    alpaca_market_data.alpaca_data_request = flaky
    original_pause = alpaca_market_data.RETRY_PAUSE_SECONDS
    alpaca_market_data.RETRY_PAUSE_SECONDS = 0
    try:
        bars, source = alpaca_market_data.fetch_eod_prices("AAPL", "2026-08-01", "2026-08-18")
        assert source == "alpaca", source
        assert flaky.attempts == 2, flaky.attempts
        assert len(bars) == 1
    finally:
        alpaca_market_data.RETRY_PAUSE_SECONDS = original_pause


def check_option_contracts() -> None:
    data = FakeData({"/v2/options/contracts": CONTRACTS})
    alpaca_market_data.alpaca_data_request = data

    rows, source = alpaca_market_data.fetch_option_contracts(
        "AAPL", expiration_gte="2026-09-01", expiration_lte="2026-09-30", option_type="CALL"
    )
    assert source == "alpaca", source
    assert len(rows) == 2
    call = rows[0]
    assert call["symbol"] == "AAPL260918C00350000"
    assert call["option_type"] == "CALL", "normalized to the adapter's uppercase vocabulary"
    assert call["strike"] == 350.0 and isinstance(call["strike"], float)
    assert call["expiration"] == "2026-09-18"
    assert call["multiplier"] == 100
    assert call["tradable"] is True

    params = data.calls[0]["params"]
    assert params["underlying_symbols"] == "AAPL"
    assert params["expiration_date_gte"] == "2026-09-01"
    assert params["expiration_date_lte"] == "2026-09-30"
    assert params["type"] == "call", "Alpaca expects lowercase type"
    # Contracts live on the trading host, not the data host.
    assert data.calls[0]["base_url"] == alpaca_market_data.ALPACA_TRADING_BASE_URL
    assert "paper-api" in data.calls[0]["base_url"], "contracts must be read from the paper host"


def check_option_chain_merge() -> None:
    data = FakeData({"/v2/options/contracts": CONTRACTS, "/v1beta1/options/snapshots/": SNAPSHOTS})
    alpaca_market_data.alpaca_data_request = data

    rows, source = alpaca_market_data.fetch_option_chain("AAPL")
    assert source == "alpaca", source
    assert len(rows) == 2
    call = next(row for row in rows if row["option_type"] == "CALL")
    assert call["symbol"] == "AAPL260918C00350000"
    assert call["bid"] == 4.60
    assert call["ask"] == 5.10
    assert call["mid"] == 4.85, "mid must be the bid/ask midpoint"
    assert call["last"] == 4.85
    assert call["strike"] == 350.0
    assert call["quoted_at"] == "2026-08-18T14:00:25Z"

    put = next(row for row in rows if row["option_type"] == "PUT")
    assert put["bid"] == 2.90 and put["ask"] == 3.30
    assert put["mid"] == 3.10

    # Filtering by type narrows the merged chain.
    calls_only, _ = alpaca_market_data.fetch_option_chain("AAPL", option_type="CALL")
    assert [row["option_type"] for row in calls_only] == ["CALL"]

    # A contract with no snapshot still appears, with empty quote fields.
    partial = FakeData({"/v2/options/contracts": CONTRACTS, "/v1beta1/options/snapshots/": {"snapshots": {}}})
    alpaca_market_data.alpaca_data_request = partial
    rows, _ = alpaca_market_data.fetch_option_chain("AAPL")
    assert len(rows) == 2
    assert rows[0]["bid"] is None and rows[0]["mid"] is None


def check_summarize_history_routes_to_alpaca() -> None:
    import market_data

    data = FakeData({"/v2/stocks/AAPL/bars": {"__pages__": {None: BAR_PAGE_1, "PAGE2": BAR_PAGE_2}}})
    alpaca_market_data.alpaca_data_request = data

    os.environ["MARKET_DATA_PROVIDER"] = "alpaca"
    summary = market_data.summarize_history("AAPL", days=30, min_bars=2)
    assert summary["source"] == "alpaca", summary
    assert summary["bars"] == 3
    assert summary["latest_close"] == 315.2
    assert summary["latest_date"] == "2026-08-10"
    assert summary["enough_history"] is True

    def poison(*args, **kwargs):
        raise AssertionError("provider=tiingo must not reach the Alpaca adapter")

    alpaca_market_data.alpaca_data_request = poison
    os.environ["MARKET_DATA_PROVIDER"] = "tiingo"
    original_tiingo = market_data.fetch_tiingo_eod_prices
    market_data.fetch_tiingo_eod_prices = lambda *a, **k: ([{"symbol": "AAPL", "date": "2026-08-10", "close": 1.0}], "tiingo")
    try:
        summary = market_data.summarize_history("AAPL", days=30, min_bars=1)
        assert summary["source"] == "tiingo", summary
    finally:
        market_data.fetch_tiingo_eod_prices = original_tiingo
        os.environ["MARKET_DATA_PROVIDER"] = "alpaca"


def main() -> None:
    saved = {k: os.environ.get(k) for k in ["ALPACA_API_KEY_ID", "ALPACA_SECRET_KEY", "MARKET_DATA_PROVIDER"]}
    original_request = alpaca_market_data.alpaca_data_request
    os.environ["ALPACA_API_KEY_ID"] = "TEST-KEY-ID"
    os.environ["ALPACA_SECRET_KEY"] = "TEST-SECRET"
    os.environ["MARKET_DATA_PROVIDER"] = "alpaca"
    try:
        check_bar_normalization_and_paging()
        check_fallback_and_cache_paths()
        check_sip_fallback_to_iex()
        check_transient_network_retry()
        check_option_contracts()
        check_option_chain_merge()
        check_summarize_history_routes_to_alpaca()
    finally:
        alpaca_market_data.alpaca_data_request = original_request
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    print("PASS: Alpaca market data returns normalized bars and Level 1 option chains.")


if __name__ == "__main__":
    main()
