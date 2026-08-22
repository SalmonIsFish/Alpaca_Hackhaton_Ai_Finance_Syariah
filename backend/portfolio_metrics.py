"""Risk-adjusted return metrics computed from the account's real Alpaca equity curve.

Reads GET /v2/account/portfolio/history and reports Sortino, Sharpe, max drawdown
and cumulative return over the window. Nothing here trades, and nothing here
decides -- it reports what already happened.

**The risk-free rate is 0, deliberately.** A conventional Sharpe ratio divides
excess return over a T-bill rate, which is an interest rate. Embedding one in the
performance metric of a system built to exclude Riba would contradict the thing
the system exists to enforce, so the excess-return term is dropped rather than
borrowed from a conventional benchmark. That makes the numbers here conservative
against a conventional entrant rather than flattering: with rf = 0 the whole
return is treated as risk-taking, none of it as a guaranteed baseline.

**Sortino leads, Sharpe follows.** Sharpe penalises upside and downside variance
equally. Sortino only counts downside deviation, which is the honest measure for
a strategy whose pitch is capital preservation and lower tail risk rather than
raw return.

Read the observation count before quoting any of it. Over a handful of trading
days these ratios are arithmetic, not evidence, and the output says so.

    python backend/portfolio_metrics.py
    python backend/portfolio_metrics.py --period 1M --json
"""

import json
import math
import sys

import alpaca_market_data
from alpaca_market_data import ALPACA_TRADING_BASE_URL
from alpaca_paper_adapter import alpaca_credentials


PORTFOLIO_HISTORY_PATH = "/v2/account/portfolio/history"

# Daily bars, so variance scales by the square root of the trading days in a year.
TRADING_DAYS_PER_YEAR = 252

# Below this many daily returns, a ratio is noise dressed as a number.
MIN_OBSERVATIONS = 2

# The point at which the window is long enough to be worth quoting unqualified.
MEANINGFUL_OBSERVATIONS = 20


def fetch_portfolio_history(
    *, credentials: dict, period: str = "1M", timeframe: str = "1D"
) -> dict:
    """The account equity curve, straight from the broker.

    Goes through alpaca_market_data.alpaca_data_request rather than
    alpaca_paper_adapter.alpaca_request because that seam already takes query
    params and already points at paper-api for /v2/options/contracts. Widening the
    adapter's seam would touch the module every execution test mocks, for nothing.
    """
    response = alpaca_market_data.alpaca_data_request(
        PORTFOLIO_HISTORY_PATH,
        {"period": period, "timeframe": timeframe, "extended_hours": "false"},
        credentials=credentials,
        base_url=ALPACA_TRADING_BASE_URL,
    )
    if not response.get("ok"):
        raise SystemExit(
            f"portfolio history request failed: {response.get('reason') or response.get('status_code')}"
        )
    data = response.get("data")
    return data if isinstance(data, dict) else {}


def daily_returns(equity: list) -> list[float]:
    """Simple period-over-period returns, skipping bars that cannot produce one.

    A zero or absent prior value is dropped rather than treated as a 0% return:
    Alpaca pads the series before the account was funded, and dividing by it would
    manufacture either a division error or a fake flat day.
    """
    returns = []
    previous = None
    for raw in equity or []:
        try:
            value = float(raw)
        except (TypeError, ValueError):
            previous = None
            continue
        if previous is not None and previous > 0:
            returns.append(value / previous - 1.0)
        previous = value
    return returns


def max_drawdown(equity: list) -> float | None:
    """Deepest peak-to-trough fall in the window, as a negative fraction."""
    peak = None
    worst = 0.0
    seen = False
    for raw in equity or []:
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if value <= 0:
            continue
        seen = True
        if peak is None or value > peak:
            peak = value
        elif peak:
            worst = min(worst, value / peak - 1.0)
    return worst if seen else None


def compute_metrics(history: dict) -> dict:
    """Turn an equity curve into the reported metrics, or say why it cannot."""
    equity = history.get("equity") or []
    returns = daily_returns(equity)
    observations = len(returns)

    base = {
        "observations": observations,
        "timeframe": history.get("timeframe"),
        "risk_free_rate": 0.0,
        "annualization_factor": TRADING_DAYS_PER_YEAR,
    }

    if observations < MIN_OBSERVATIONS:
        # Fail closed rather than print a confident-looking ratio built on one bar.
        return {
            **base,
            "status": "INSUFFICIENT_HISTORY",
            "reason": (
                f"{observations} daily return(s); at least {MIN_OBSERVATIONS} are needed "
                "before a ratio means anything"
            ),
        }

    mean = sum(returns) / observations
    variance = sum((value - mean) ** 2 for value in returns) / (observations - 1)
    stdev = math.sqrt(variance)
    # Downside deviation targets 0, matching rf = 0: a losing day is the risk, and
    # the divisor is the full observation count, not just the losing days.
    downside = math.sqrt(sum(min(value, 0.0) ** 2 for value in returns) / observations)
    scale = math.sqrt(TRADING_DAYS_PER_YEAR)

    equity_values = [float(value) for value in equity if _is_number(value)]
    positive = [value for value in equity_values if value > 0]
    cumulative = (positive[-1] / positive[0] - 1.0) if len(positive) >= 2 else None

    notes = []
    sharpe = None
    if stdev > 0:
        sharpe = mean / stdev * scale
    else:
        notes.append("equity did not move in this window, so Sharpe is undefined")

    sortino = None
    if downside > 0:
        sortino = mean / downside * scale
    else:
        # Not an infinite Sortino -- an undefined one. There is no downside to divide by.
        notes.append("no losing days in this window, so Sortino is undefined rather than infinite")

    if observations < MEANINGFUL_OBSERVATIONS:
        notes.append(
            f"only {observations} daily observations -- too short a window to quote as evidence "
            "of skill; report it with the count attached"
        )

    return {
        **base,
        "status": "OK",
        "mean_daily_return": mean,
        "daily_volatility": stdev,
        "downside_deviation": downside,
        "annualized_volatility": stdev * scale,
        "sharpe_rf_zero": sharpe,
        "sortino_rf_zero": sortino,
        "max_drawdown": max_drawdown(equity),
        "cumulative_return": cumulative,
        "best_day": max(returns),
        "worst_day": min(returns),
        "notes": notes,
    }


def _is_number(value) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _pct(value) -> str:
    return "n/a" if value is None else f"{value * 100:.2f}%"


def _ratio(value) -> str:
    return "undefined" if value is None else f"{value:.2f}"


def _flag(name: str) -> bool:
    return name in sys.argv


def _option(name: str, default: str) -> str:
    """Read `--name value`, matching the flag style the other scripts here use."""
    if name in sys.argv:
        index = sys.argv.index(name)
        if index + 1 < len(sys.argv):
            return sys.argv[index + 1]
    return default


def main() -> int:
    credentials = alpaca_credentials()
    if not credentials:
        raise SystemExit("ALPACA_API_KEY_ID / ALPACA_SECRET_KEY are not configured")

    period = _option("--period", "1M")
    timeframe = _option("--timeframe", "1D")
    history = fetch_portfolio_history(credentials=credentials, period=period, timeframe=timeframe)
    metrics = compute_metrics(history)

    if _flag("--json"):
        print(json.dumps(metrics, indent=2, sort_keys=True))
        return 0 if metrics["status"] == "OK" else 1

    print(f"window:    period={period} timeframe={timeframe}")
    print(f"observations: {metrics['observations']} daily returns")

    if metrics["status"] != "OK":
        print(f"status:    {metrics['status']}")
        print(f"           {metrics['reason']}")
        return 1

    print("")
    print(f"sortino:   {_ratio(metrics['sortino_rf_zero'])}   (rf = 0, annualized)")
    print(f"sharpe:    {_ratio(metrics['sharpe_rf_zero'])}   (rf = 0, annualized)")
    print(f"max dd:    {_pct(metrics['max_drawdown'])}")
    print(f"return:    {_pct(metrics['cumulative_return'])} over the window")
    print("")
    print(
        f"daily vol: {_pct(metrics['daily_volatility'])}   annualized {_pct(metrics['annualized_volatility'])}"
    )
    print(f"downside:  {_pct(metrics['downside_deviation'])}")
    print(f"best day:  {_pct(metrics['best_day'])}    worst day: {_pct(metrics['worst_day'])}")
    print("")
    print("risk-free rate is 0 by design: a conventional benchmark is an interest rate,")
    print("and this system exists to exclude Riba. Sortino leads because the strategy")
    print("claims lower tail risk, not higher raw return.")
    for note in metrics["notes"]:
        print(f"note:      {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
