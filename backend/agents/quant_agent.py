"""Local quant agent for rule-based signal evaluation."""

from datetime import date, datetime, timezone, timedelta

# Route through the provider switch rather than a single vendor: pinning the quant
# agent to tiingo let a tiingo outage blank the signal while the configured provider
# (MARKET_DATA_PROVIDER, alpaca by default) was healthy. The on-disk cache is shared
# by both providers, so cache metadata still comes from tiingo_prices.
import market_data
from tiingo_prices import read_cache_metadata


def _evaluate_s001_signal(bars: list[dict]) -> dict:
    if len(bars) < 200:
        return {"signal": "NO_SIGNAL", "reason": "insufficient_history", "required_bars": 200, "received_bars": len(bars)}

    closes = [float(bar["close"]) for bar in bars]
    sma50 = sum(closes[-50:]) / 50
    sma200 = sum(closes[-200:]) / 200
    breakout_level = max(closes[-56:-1])
    latest_close = closes[-1]
    trend_ok = sma50 > sma200
    breakout = latest_close >= breakout_level
    breakout_gap_pct = round(((latest_close / breakout_level) - 1) * 100, 4) if breakout_level else None
    if trend_ok and breakout:
        return {
            "signal": "BUY",
            "reason": "trend_and_breakout_confirmed",
            "sma50": sma50,
            "sma200": sma200,
            "trend_ok": trend_ok,
            "breakout_ok": breakout,
            "breakout_level": breakout_level,
            "breakout_gap_pct": breakout_gap_pct,
        }
    return {
        "signal": "NO_SIGNAL",
        "reason": "strategy_conditions_not_met",
        "sma50": sma50,
        "sma200": sma200,
        "trend_ok": trend_ok,
        "breakout_ok": breakout,
        "breakout_level": breakout_level,
        "breakout_gap_pct": breakout_gap_pct,
    }


def evaluate_quant(symbol: str, *, allow_fallback: bool = True, allow_stale_cache: bool = False) -> dict:
    end_date = date.today()
    start_date = end_date - timedelta(days=320)
    bars, source = market_data.fetch_eod_prices(
        symbol,
        start_date.isoformat(),
        end_date.isoformat(),
        allow_fallback=allow_fallback,
        allow_stale_cache=allow_stale_cache,
    )
    freshness = data_freshness(symbol, source)
    strategy = _evaluate_s001_signal(bars)
    close = float(bars[-1]["close"]) if bars else None
    return {
        "agent": "quant",
        "status": "PASS" if strategy.get("signal") == "BUY" else "NO_SIGNAL",
        "symbol": symbol,
        "signal": strategy.get("signal"),
        "reason": strategy.get("reason"),
        "price": close,
        "bars": len(bars),
        "price_source": source,
        **freshness,
        "strategy": strategy,
    }


LIVE_SOURCES = {"tiingo", "alpaca", "alpaca_iex"}


def data_freshness(symbol: str, source: str) -> dict:
    if source in LIVE_SOURCES:
        return {"data_freshness": "live", "cache_cached_at": None, "cache_age_hours": None}
    if "_cache" not in source:
        return {"data_freshness": "fixture" if source.startswith("fixture") else "unknown", "cache_cached_at": None, "cache_age_hours": None}
    metadata = read_cache_metadata(symbol)
    cached_at = metadata.get("cached_at")
    age_hours = None
    if cached_at:
        try:
            cached_dt = datetime.fromisoformat(cached_at)
            if cached_dt.tzinfo is None:
                cached_dt = cached_dt.replace(tzinfo=timezone.utc)
            age_hours = round((datetime.now(timezone.utc) - cached_dt).total_seconds() / 3600, 2)
        except ValueError:
            age_hours = None
    return {"data_freshness": "cached", "cache_cached_at": cached_at, "cache_age_hours": age_hours}
