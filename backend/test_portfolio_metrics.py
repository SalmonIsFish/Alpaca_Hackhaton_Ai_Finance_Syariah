"""Verify portfolio_metrics computes risk-adjusted returns from a real equity curve.

The network is never touched: alpaca_market_data.alpaca_data_request is the seam
every Alpaca data call goes through, and it is swapped here for a recorder, the
same convention test_alpaca_market_data.py uses.

Assertions target the *request that was built* as well as the numbers that came
out -- a metrics script that silently queried the wrong window would still print a
perfectly plausible Sharpe ratio.
"""

import math

import alpaca_market_data
import portfolio_metrics


def install(payload, ok=True):
    """Point the data seam at one canned response and record what was asked for."""
    calls = []

    def fake_request(path, params, *, credentials, base_url=None):
        calls.append(
            {"path": path, "params": params, "credentials": credentials, "base_url": base_url}
        )
        if not ok:
            return {"ok": False, "status_code": 500, "data": {}, "reason": "http_500"}
        return {"ok": True, "status_code": 200, "data": payload}

    alpaca_market_data.alpaca_data_request = fake_request
    return calls


def main() -> None:
    real_request = alpaca_market_data.alpaca_data_request
    try:
        run_all()
    finally:
        alpaca_market_data.alpaca_data_request = real_request


def run_all() -> None:
    # ------------------------------------------------------- the request built
    calls = install({"equity": [100.0, 101.0, 100.0], "timeframe": "1D"})
    portfolio_metrics.fetch_portfolio_history(
        credentials={"key_id": "k", "secret_key": "s"}, period="1W", timeframe="1D"
    )
    assert len(calls) == 1, calls
    assert calls[0]["path"] == "/v2/account/portfolio/history", calls[0]
    assert calls[0]["params"]["period"] == "1W", calls[0]
    assert calls[0]["params"]["timeframe"] == "1D", calls[0]
    assert calls[0]["params"]["extended_hours"] == "false", calls[0]
    # Portfolio history is a trading-API endpoint, not a market-data one. Sent to
    # the data host it would 404, and the default base_url is the data host.
    assert calls[0]["base_url"] == alpaca_market_data.ALPACA_TRADING_BASE_URL, calls[0]

    # A broker failure must not become a silent zero-return series.
    install({}, ok=False)
    try:
        portfolio_metrics.fetch_portfolio_history(credentials={"key_id": "k", "secret_key": "s"})
        raise AssertionError("a failed history request should not return quietly")
    except SystemExit as exc:
        assert "http_500" in str(exc), exc

    # ------------------------------------------------------------ the returns
    # Padding before the account was funded must not manufacture a return.
    padded = portfolio_metrics.daily_returns([0, 0, 100.0, 110.0])
    assert len(padded) == 1 and abs(padded[0] - 0.1) < 1e-12, padded
    assert portfolio_metrics.daily_returns([100.0, None, 110.0]) == []
    assert portfolio_metrics.daily_returns([]) == []
    assert portfolio_metrics.daily_returns([100.0]) == []

    # ---------------------------------------------------------- the arithmetic
    # Returns are +10%, -10%, +10%. Hand-computed below rather than asserted
    # against the code's own output, which would only prove it is self-consistent.
    metrics = portfolio_metrics.compute_metrics(
        {"equity": [100.0, 110.0, 99.0, 108.9], "timeframe": "1D"}
    )
    assert metrics["status"] == "OK", metrics
    assert metrics["observations"] == 3, metrics
    assert metrics["risk_free_rate"] == 0.0, metrics

    returns = [0.1, -0.1, 0.1]
    mean = sum(returns) / 3
    variance = sum((value - mean) ** 2 for value in returns) / 2
    stdev = math.sqrt(variance)
    downside = math.sqrt((0.1**2) / 3)
    scale = math.sqrt(252)

    assert abs(metrics["mean_daily_return"] - mean) < 1e-12, metrics
    assert abs(metrics["daily_volatility"] - stdev) < 1e-12, metrics
    assert abs(metrics["downside_deviation"] - downside) < 1e-12, metrics
    assert abs(metrics["sharpe_rf_zero"] - mean / stdev * scale) < 1e-9, metrics
    assert abs(metrics["sortino_rf_zero"] - mean / downside * scale) < 1e-9, metrics
    # Sortino must exceed Sharpe here: two of the three moves are upside, and only
    # Sharpe is penalised for them.
    assert metrics["sortino_rf_zero"] > metrics["sharpe_rf_zero"], metrics
    assert abs(metrics["best_day"] - 0.1) < 1e-12, metrics
    assert abs(metrics["worst_day"] + 0.1) < 1e-12, metrics
    assert abs(metrics["cumulative_return"] - 0.089) < 1e-9, metrics
    # Peak 110 to trough 99 is -10%, deeper than the -10% single-day move only
    # because it is measured from the peak rather than the prior bar.
    assert abs(metrics["max_drawdown"] + 0.1) < 1e-12, metrics

    # --------------------------------------------------------- thin windows
    thin = portfolio_metrics.compute_metrics({"equity": [100.0, 105.0], "timeframe": "1D"})
    assert thin["status"] == "INSUFFICIENT_HISTORY", thin
    assert thin["observations"] == 1, thin
    assert "sharpe_rf_zero" not in thin, thin
    empty = portfolio_metrics.compute_metrics({})
    assert empty["status"] == "INSUFFICIENT_HISTORY", empty

    # A short-but-computable window still carries the warning, so a number from it
    # cannot be quoted as evidence without the caveat travelling with it.
    assert any("too short a window" in note for note in metrics["notes"]), metrics

    # ------------------------------------------------------- undefined ratios
    # Every day up: there is no downside to divide by, so Sortino is undefined
    # rather than infinite, and the run must not raise.
    rising = portfolio_metrics.compute_metrics(
        {"equity": [100.0, 101.0, 102.0, 103.0], "timeframe": "1D"}
    )
    assert rising["status"] == "OK", rising
    assert rising["sortino_rf_zero"] is None, rising
    assert any("no losing days" in note for note in rising["notes"]), rising
    assert rising["sharpe_rf_zero"] is not None, rising

    # Perfectly flat equity: no variance at all, so Sharpe is undefined too.
    flat = portfolio_metrics.compute_metrics({"equity": [100.0, 100.0, 100.0], "timeframe": "1D"})
    assert flat["status"] == "OK", flat
    assert flat["sharpe_rf_zero"] is None, flat
    assert flat["sortino_rf_zero"] is None, flat
    assert abs(flat["max_drawdown"]) < 1e-12, flat

    print("PASS: portfolio metrics report Sortino and Sharpe at rf=0 and refuse thin windows.")


if __name__ == "__main__":
    main()
