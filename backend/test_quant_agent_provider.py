"""Verify the quant agent reads prices through the configured market-data provider.

The quant signal is the first thing /paper/preview consults, so if it is pinned to
one provider it can block every order while the configured provider is healthy.
Nothing here touches the network: market_data.fetch_eod_prices is the seam, exactly
as alpaca_request is elsewhere.
"""

import os

import agents.quant_agent as quant_agent
import market_data


def trending_bars(symbol: str, count: int = 260) -> list[dict]:
    """A monotonically rising series, so SMA50 > SMA200 and the last close breaks out."""
    bars = []
    for index in range(count):
        close = 100.0 + index
        bars.append(
            {
                "symbol": symbol,
                "date": f"2026-01-{(index % 28) + 1:02d}",
                "open": close,
                "high": close,
                "low": close,
                "close": close,
                "volume": 1000,
            }
        )
    return bars


def test_quant_agent_uses_the_provider_switch() -> None:
    """A tiingo outage must not blind the quant agent when the provider is alpaca."""
    calls = []

    def fake_fetch(symbol, start_date, end_date, **kwargs):
        calls.append(symbol)
        return trending_bars(symbol), "alpaca"

    original = market_data.fetch_eod_prices
    market_data.fetch_eod_prices = fake_fetch
    try:
        result = quant_agent.evaluate_quant("CVX")
    finally:
        market_data.fetch_eod_prices = original

    assert calls == ["CVX"], f"quant agent bypassed the provider switch: {calls}"
    assert result["price_source"] == "alpaca", result["price_source"]
    assert result["signal"] == "BUY", result
    assert result["status"] == "PASS", result


def test_alpaca_sources_are_reported_live_not_unknown() -> None:
    """data_freshness predated the alpaca provider; alpaca bars are live, not unknown."""
    for source in ["alpaca", "alpaca_iex", "tiingo"]:
        freshness = quant_agent.data_freshness("CVX", source)
        assert freshness["data_freshness"] == "live", (source, freshness)

    for source in ["fixture", "fixture_after_tiingo_error", "fixture_after_alpaca_error"]:
        freshness = quant_agent.data_freshness("CVX", source)
        assert freshness["data_freshness"] == "fixture", (source, freshness)

    for source in ["tiingo_cache_after_error", "alpaca_cache_after_error", "alpaca_cache_no_credentials"]:
        freshness = quant_agent.data_freshness("CVX", source)
        assert freshness["data_freshness"] == "cached", (source, freshness)


def test_provider_switch_honours_the_configured_provider() -> None:
    """market_data.fetch_eod_prices is the switch; confirm it actually switches."""
    saved = os.environ.get("MARKET_DATA_PROVIDER")
    seen = {}

    import alpaca_market_data
    import tiingo_prices

    original_alpaca = alpaca_market_data.fetch_eod_prices
    original_tiingo = tiingo_prices.fetch_eod_prices
    original_switch_alpaca = market_data.fetch_alpaca_eod_prices
    original_switch_tiingo = market_data.fetch_tiingo_eod_prices

    market_data.fetch_alpaca_eod_prices = lambda *a, **k: (seen.setdefault("provider", "alpaca"), ([], "alpaca"))[1]
    market_data.fetch_tiingo_eod_prices = lambda *a, **k: (seen.setdefault("provider", "tiingo"), ([], "tiingo"))[1]
    try:
        os.environ["MARKET_DATA_PROVIDER"] = "alpaca"
        market_data.fetch_eod_prices("CVX", "2026-01-01", "2026-08-19")
        assert seen["provider"] == "alpaca", seen

        seen.clear()
        os.environ["MARKET_DATA_PROVIDER"] = "tiingo"
        market_data.fetch_eod_prices("CVX", "2026-01-01", "2026-08-19")
        assert seen["provider"] == "tiingo", seen
    finally:
        market_data.fetch_alpaca_eod_prices = original_switch_alpaca
        market_data.fetch_tiingo_eod_prices = original_switch_tiingo
        alpaca_market_data.fetch_eod_prices = original_alpaca
        tiingo_prices.fetch_eod_prices = original_tiingo
        if saved is None:
            os.environ.pop("MARKET_DATA_PROVIDER", None)
        else:
            os.environ["MARKET_DATA_PROVIDER"] = saved


def main() -> None:
    test_quant_agent_uses_the_provider_switch()
    test_alpaca_sources_are_reported_live_not_unknown()
    test_provider_switch_honours_the_configured_provider()
    print("PASS: the quant agent reads through the configured market-data provider.")


if __name__ == "__main__":
    main()
