"""Verify Tiingo diagnostics and local cache behavior without network calls."""

import json
import tempfile
from pathlib import Path
from urllib.error import HTTPError

import tiingo_prices


class FakeSettings:
    tiingo_api_token = "test-token"


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return json.dumps(
            [
                {
                    "date": "2026-07-21T00:00:00.000Z",
                    "open": 10.0,
                    "high": 11.0,
                    "low": 9.0,
                    "close": 10.5,
                    "volume": 1000,
                }
            ]
        ).encode("utf-8")


def main() -> None:
    original_cache_dir = tiingo_prices.CACHE_DIR
    original_load_settings = tiingo_prices.load_settings
    original_urlopen = tiingo_prices.urlopen
    temp_dir = tempfile.TemporaryDirectory()
    try:
        tiingo_prices.CACHE_DIR = Path(temp_dir.name)
        tiingo_prices.load_settings = lambda: FakeSettings()

        tiingo_prices.urlopen = lambda request, timeout=15: FakeResponse()
        bars, source = tiingo_prices.fetch_eod_prices(
            "aapl",
            "2026-01-01",
            "2026-07-22",
            allow_fallback=False,
        )
        assert source == "tiingo"
        assert bars[0]["symbol"] == "AAPL"
        assert (Path(temp_dir.name) / "AAPL.json").exists()
        metadata = tiingo_prices.read_cache_metadata("AAPL")
        assert metadata["symbol"] == "AAPL"
        assert metadata["cached_at"]

        def raise_rate_limit(request, timeout=15):
            raise HTTPError(
                url="https://api.tiingo.com",
                code=429,
                msg="Too Many Requests",
                hdrs={"Retry-After": "3600"},
                fp=None,
            )

        tiingo_prices.urlopen = raise_rate_limit
        cached_bars, cached_source = tiingo_prices.fetch_eod_prices(
            "AAPL",
            "2026-01-01",
            "2026-07-22",
            allow_fallback=False,
            allow_stale_cache=True,
        )
        assert cached_source == "tiingo_cache_after_error"
        assert cached_bars == bars

        try:
            tiingo_prices.fetch_eod_prices(
                "MSFT",
                "2026-01-01",
                "2026-07-22",
                allow_fallback=False,
            )
        except tiingo_prices.TiingoDataError as exc:
            assert exc.error_code == "http_429"
            assert exc.status_code == 429
            assert exc.retry_after == "3600"
        else:
            raise AssertionError("expected TiingoDataError")
    finally:
        tiingo_prices.CACHE_DIR = original_cache_dir
        tiingo_prices.load_settings = original_load_settings
        tiingo_prices.urlopen = original_urlopen
        temp_dir.cleanup()

    print("PASS: Tiingo cache and diagnostics are safe.")


if __name__ == "__main__":
    main()
