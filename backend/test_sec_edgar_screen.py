"""Verify sec_edgar_screen implements the SC two-tier screen and fails closed.

The network is never touched: sec_edgar_screen.sec_request is the single seam every
SEC call goes through, and every test here swaps it for a canned URL->payload map,
the same convention alpaca_request uses in test_alpaca_paper_adapter.py.

Assertions target the *decision and its evidence*, not just the status string --
which concepts a ratio was built from, and which balance-sheet date it came from.
"""

import sqlite3

import sec_edgar_screen


TICKER_MAP = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 19617, "ticker": "JPM", "title": "JPMorgan Chase & Co."},
    "2": {"cik_str": 21344, "ticker": "KO", "title": "Coca-Cola Co"},
    "3": {"cik_str": 764180, "ticker": "MO", "title": "Altria Group, Inc."},
}


def submissions(name, sic, sic_description, exchange="Nasdaq"):
    return {"name": name, "sic": sic, "sicDescription": sic_description, "exchanges": [exchange]}


def usd(*rows):
    return {"units": {"USD": list(rows)}}


def row(end, val, form="10-K", filed="2026-02-01"):
    return {"end": end, "val": val, "form": form, "filed": filed}


def facts(**concepts):
    return {"facts": {"us-gaap": concepts}}


# Every verdict check_us_symbol recorded during the current install(), so the
# audit-log write can be asserted without the suite ever opening the real
# paper_trading.db.
RECORDED = []


def install(responses, missing_ok=False):
    """Point the seam at a canned {url: payload} map and reset the CIK cache."""
    sec_edgar_screen.reset_ticker_cache()
    calls = []
    RECORDED.clear()
    sec_edgar_screen._record_screen = RECORDED.append

    def fake_request(url):
        calls.append(url)
        if url in responses:
            value = responses[url]
            if isinstance(value, dict) and "ok" in value:
                return value
            return {"ok": True, "status_code": 200, "data": value}
        if missing_ok:
            return {"ok": False, "status_code": 404, "data": {}, "reason": "http_404"}
        raise AssertionError(f"unexpected SEC request: {url}")

    sec_edgar_screen.sec_request = fake_request
    return calls


def urls(cik):
    return (
        sec_edgar_screen.SEC_SUBMISSIONS_URL.format(cik=cik),
        sec_edgar_screen.SEC_FACTS_URL.format(cik=cik),
    )


TICKERS_URL = sec_edgar_screen.SEC_TICKERS_URL


def main() -> None:
    real_request = sec_edgar_screen.sec_request
    real_record = sec_edgar_screen._record_screen
    try:
        run_all()
    finally:
        sec_edgar_screen.sec_request = real_request
        sec_edgar_screen._record_screen = real_record
        sec_edgar_screen.reset_ticker_cache()


def run_all() -> None:
    # ---------------------------------------------------------------- tier 1
    # A conventional bank is disqualified on business activity alone. Its own
    # balance sheet would pass neither ratio, but the point is that no ratio is
    # computed at all -- the company facts endpoint must never be called.
    submissions_url, facts_url = urls(19617)
    calls = install(
        {
            TICKERS_URL: TICKER_MAP,
            submissions_url: submissions("JPMORGAN CHASE & CO", 6021, "National Commercial Banks", "NYSE"),
        }
    )
    bank = sec_edgar_screen.check_us_symbol("JPM")
    assert bank["status"] == "NON_COMPLIANT", bank
    assert bank["screen"] == "business_activity", bank
    assert "conventional banking" in bank["reason"], bank
    assert bank["exchange"] == "NYSE", bank
    assert facts_url not in calls, "business-activity exclusion must short-circuit before the ratio fetch"

    # Tobacco is excluded the same way, on the SIC block rather than one code.
    submissions_url, _ = urls(764180)
    install({TICKERS_URL: TICKER_MAP, submissions_url: submissions("ALTRIA GROUP", 2111, "Cigarettes", "NYSE")})
    tobacco = sec_edgar_screen.check_us_symbol("MO")
    assert tobacco["status"] == "NON_COMPLIANT", tobacco
    assert "tobacco" in tobacco["reason"], tobacco

    # Every category in the exclusion table must resolve to a label; a range added
    # without one would raise KeyError at screen time instead of at import time.
    for (low, high), category in sec_edgar_screen.EXCLUDED_SIC_RANGES:
        assert category in sec_edgar_screen.EXCLUSION_LABELS, category
        assert low <= high, (low, high)
        assert sec_edgar_screen.business_activity_exclusion(low) == category
        assert sec_edgar_screen.business_activity_exclusion(high) == category

    # A benign manufacturer is not excluded, and neither is an unclassified filer --
    # tier 1 abstains there and lets the ratios decide.
    assert sec_edgar_screen.business_activity_exclusion(3571) is None
    assert sec_edgar_screen.business_activity_exclusion(None) is None

    # ---------------------------------------------------------------- tier 2
    # Comfortably inside both limits: debt 20%, cash 10%.
    submissions_url, facts_url = urls(320193)
    clean = {
        TICKERS_URL: TICKER_MAP,
        submissions_url: submissions("Apple Inc.", 3571, "Electronic Computers"),
        facts_url: facts(
            Assets=usd(row("2025-09-27", 1_000.0)),
            LongTermDebtNoncurrent=usd(row("2025-09-27", 150.0)),
            LongTermDebtCurrent=usd(row("2025-09-27", 50.0)),
            CashAndCashEquivalentsAtCarryingValue=usd(row("2025-09-27", 100.0)),
        ),
    }
    install(clean)
    passing = sec_edgar_screen.check_us_symbol("AAPL")
    assert passing["status"] == "COMPLIANT", passing
    assert passing["screen"] == "financial_ratios", passing
    assert passing["report_date"] == "2025-09-27", passing
    assert passing["ratios"]["debt_ratio_pct"] == 20.0, passing
    assert passing["ratios"]["cash_ratio_pct"] == 10.0, passing
    # The evidence trail names the tags the ratio was actually built from.
    assert passing["ratios"]["debt_concepts_used"] == ["LongTermDebtNoncurrent", "LongTermDebtCurrent"], passing
    assert passing["ratios"]["cash_concepts_used"] == ["CashAndCashEquivalentsAtCarryingValue"], passing

    # Lower case in, upper case out: symbol normalisation reaches the CIK lookup.
    install(clean)
    assert sec_edgar_screen.check_us_symbol("  aapl ")["symbol"] == "AAPL"

    # Debt over the line fails, and the reason quotes the number that failed.
    install(
        {
            TICKERS_URL: TICKER_MAP,
            submissions_url: submissions("Apple Inc.", 3571, "Electronic Computers"),
            facts_url: facts(
                Assets=usd(row("2025-09-27", 1_000.0)),
                LongTermDebtNoncurrent=usd(row("2025-09-27", 400.0)),
                CashAndCashEquivalentsAtCarryingValue=usd(row("2025-09-27", 50.0)),
            ),
        }
    )
    heavy_debt = sec_edgar_screen.check_us_symbol("AAPL")
    assert heavy_debt["status"] == "NON_COMPLIANT", heavy_debt
    assert "40.0%" in heavy_debt["reason"], heavy_debt
    assert "cash" not in heavy_debt["reason"], "only the failing ratio should be reported as a failure"

    # Cash-rich balance sheet: short-term investments count toward the cash ratio,
    # so a company under the limit on cash alone can still fail on the total.
    install(
        {
            TICKERS_URL: TICKER_MAP,
            submissions_url: submissions("Apple Inc.", 3571, "Electronic Computers"),
            facts_url: facts(
                Assets=usd(row("2025-09-27", 1_000.0)),
                CashAndCashEquivalentsAtCarryingValue=usd(row("2025-09-27", 200.0)),
                ShortTermInvestments=usd(row("2025-09-27", 150.0)),
            ),
        }
    )
    cash_rich = sec_edgar_screen.check_us_symbol("AAPL")
    assert cash_rich["status"] == "NON_COMPLIANT", cash_rich
    assert cash_rich["ratios"]["cash_ratio_pct"] == 35.0, cash_rich

    # Exactly 33% is not "less than 33%" -- the boundary rejects.
    install(
        {
            TICKERS_URL: TICKER_MAP,
            submissions_url: submissions("Apple Inc.", 3571, "Electronic Computers"),
            facts_url: facts(
                Assets=usd(row("2025-09-27", 100.0)),
                LongTermDebtNoncurrent=usd(row("2025-09-27", 33.0)),
                CashAndCashEquivalentsAtCarryingValue=usd(row("2025-09-27", 1.0)),
            ),
        }
    )
    boundary = sec_edgar_screen.check_us_symbol("AAPL")
    assert boundary["status"] == "NON_COMPLIANT", boundary

    # Just under it passes.
    install(
        {
            TICKERS_URL: TICKER_MAP,
            submissions_url: submissions("Apple Inc.", 3571, "Electronic Computers"),
            facts_url: facts(
                Assets=usd(row("2025-09-27", 100.0)),
                LongTermDebtNoncurrent=usd(row("2025-09-27", 32.99)),
                CashAndCashEquivalentsAtCarryingValue=usd(row("2025-09-27", 1.0)),
            ),
        }
    )
    assert sec_edgar_screen.check_us_symbol("AAPL")["status"] == "COMPLIANT"

    # ------------------------------------------------- period selection
    # The anchor is the latest *annual* balance-sheet date, per the SC rule that the
    # screen runs off audited annual statements. A later 10-Q must not become the
    # anchor, and the debt figure must be the one tagged at the annual date.
    install(
        {
            TICKERS_URL: TICKER_MAP,
            submissions_url: submissions("Apple Inc.", 3571, "Electronic Computers"),
            facts_url: facts(
                Assets=usd(
                    row("2024-09-28", 1_000.0, filed="2024-11-01"),
                    row("2025-09-27", 1_000.0, filed="2025-11-01"),
                    row("2026-03-28", 1_000.0, form="10-Q", filed="2026-05-01"),
                ),
                LongTermDebtNoncurrent=usd(
                    row("2024-09-28", 900.0, filed="2024-11-01"),
                    row("2025-09-27", 100.0, filed="2025-11-01"),
                    row("2026-03-28", 800.0, form="10-Q", filed="2026-05-01"),
                ),
                CashAndCashEquivalentsAtCarryingValue=usd(row("2025-09-27", 10.0, filed="2025-11-01")),
            ),
        }
    )
    anchored = sec_edgar_screen.check_us_symbol("AAPL")
    assert anchored["report_date"] == "2025-09-27", anchored
    assert anchored["ratios"]["form"] == "10-K", anchored
    assert anchored["status"] == "COMPLIANT", anchored
    assert anchored["ratios"]["debt_ratio_pct"] == 10.0, anchored

    # A component tagged only at a *different* date is not borrowed across periods.
    # Here debt exists only for the prior year; counting it would give 90%.
    install(
        {
            TICKERS_URL: TICKER_MAP,
            submissions_url: submissions("Apple Inc.", 3571, "Electronic Computers"),
            facts_url: facts(
                Assets=usd(row("2025-09-27", 1_000.0)),
                LongTermDebtNoncurrent=usd(row("2024-09-28", 900.0, filed="2024-11-01")),
                CashAndCashEquivalentsAtCarryingValue=usd(row("2025-09-27", 10.0)),
            ),
        }
    )
    no_mixing = sec_edgar_screen.check_us_symbol("AAPL")
    assert no_mixing["ratios"]["debt_ratio_pct"] == 0.0, no_mixing
    assert no_mixing["ratios"]["debt_concepts_used"] == [], no_mixing

    # A later 10-Q restating the same annual date is preferred over the original.
    install(
        {
            TICKERS_URL: TICKER_MAP,
            submissions_url: submissions("Apple Inc.", 3571, "Electronic Computers"),
            facts_url: facts(
                Assets=usd(row("2025-09-27", 1_000.0, filed="2025-11-01")),
                LongTermDebtNoncurrent=usd(
                    row("2025-09-27", 100.0, filed="2025-11-01"),
                    row("2025-09-27", 250.0, form="10-Q", filed="2026-02-01"),
                ),
                CashAndCashEquivalentsAtCarryingValue=usd(row("2025-09-27", 10.0)),
            ),
        }
    )
    restated = sec_edgar_screen.check_us_symbol("AAPL")
    assert restated["ratios"]["interest_bearing_debt"] == 250.0, restated

    # Alternatives inside one component group are exclusive: the same long-term debt
    # tagged two ways must be counted once, not twice.
    install(
        {
            TICKERS_URL: TICKER_MAP,
            submissions_url: submissions("Apple Inc.", 3571, "Electronic Computers"),
            facts_url: facts(
                Assets=usd(row("2025-09-27", 1_000.0)),
                LongTermDebtNoncurrent=usd(row("2025-09-27", 100.0)),
                LongTermDebtAndCapitalLeaseObligations=usd(row("2025-09-27", 120.0)),
                LongTermDebt=usd(row("2025-09-27", 130.0)),
                CashAndCashEquivalentsAtCarryingValue=usd(row("2025-09-27", 10.0)),
            ),
        }
    )
    one_per_group = sec_edgar_screen.check_us_symbol("AAPL")
    assert one_per_group["ratios"]["interest_bearing_debt"] == 100.0, one_per_group
    assert one_per_group["ratios"]["debt_concepts_used"] == ["LongTermDebtNoncurrent"], one_per_group

    # ---------------------------------------------------------- fail closed
    # An unmapped ticker is UNKNOWN, never a guessed verdict.
    install({TICKERS_URL: TICKER_MAP})
    missing = sec_edgar_screen.check_us_symbol("ZZZZ")
    assert missing["status"] == "UNKNOWN", missing
    assert missing["reason"] == "ticker_not_found_in_sec_registry", missing

    # An empty symbol never reaches the network.
    calls = install({})
    blank = sec_edgar_screen.check_us_symbol("   ")
    assert blank["status"] == "UNKNOWN" and blank["reason"] == "symbol_required", blank
    assert calls == [], calls

    # A failed ticker-map fetch is ERROR, and the cache is not poisoned with a
    # half-built map -- the next call must retry the fetch.
    calls = install({}, missing_ok=True)
    down = sec_edgar_screen.check_us_symbol("AAPL")
    assert down["status"] == "ERROR", down
    assert "sec_ticker_map_unavailable" in down["reason"], down
    sec_edgar_screen.check_us_symbol("AAPL")
    assert calls == [TICKERS_URL, TICKERS_URL], calls

    # A rate-limited or broken company-facts fetch is ERROR, not a pass.
    install(
        {
            TICKERS_URL: TICKER_MAP,
            submissions_url: submissions("Apple Inc.", 3571, "Electronic Computers"),
            facts_url: {"ok": False, "status_code": 429, "data": {}, "reason": "http_429"},
        }
    )
    throttled = sec_edgar_screen.check_us_symbol("AAPL")
    assert throttled["status"] == "ERROR", throttled
    assert "sec_company_facts_unavailable" in throttled["reason"], throttled

    # No total assets -> UNKNOWN. Dividing by a missing denominator is not a verdict.
    install(
        {
            TICKERS_URL: TICKER_MAP,
            submissions_url: submissions("Apple Inc.", 3571, "Electronic Computers"),
            facts_url: facts(CashAndCashEquivalentsAtCarryingValue=usd(row("2025-09-27", 10.0))),
        }
    )
    no_assets = sec_edgar_screen.check_us_symbol("AAPL")
    assert no_assets["status"] == "UNKNOWN", no_assets
    assert no_assets["reason"] == "total_assets_not_reported_in_any_filing", no_assets

    # Total assets reported only in a 10-Q is not an annual anchor -> UNKNOWN. This is
    # a real case, not a hypothetical: a reorganised filer under a fresh CIK has
    # quarterly figures for months before its first 10-K. It reports a distinct reason
    # from "no data at all" so a human triaging the UNKNOWN can tell the two apart.
    install(
        {
            TICKERS_URL: TICKER_MAP,
            submissions_url: submissions("Apple Inc.", 3571, "Electronic Computers"),
            facts_url: facts(
                Assets=usd(row("2026-03-28", 1_000.0, form="10-Q")),
                CashAndCashEquivalentsAtCarryingValue=usd(row("2026-03-28", 10.0, form="10-Q")),
            ),
        }
    )
    quarterly_only = sec_edgar_screen.check_us_symbol("AAPL")
    assert quarterly_only["status"] == "UNKNOWN", quarterly_only
    assert quarterly_only["reason"] == "no_annual_report_filed_yet_only_quarterly_data_available", quarterly_only

    # This is the important one: a balance sheet with no cash tag we recognise must
    # NOT be scored as 0% cash. Zero debt plus zero cash would otherwise read as a
    # spotless COMPLIANT built entirely out of absent data.
    install(
        {
            TICKERS_URL: TICKER_MAP,
            submissions_url: submissions("Apple Inc.", 3571, "Electronic Computers"),
            facts_url: facts(Assets=usd(row("2025-09-27", 1_000.0))),
        }
    )
    untaggable = sec_edgar_screen.check_us_symbol("AAPL")
    assert untaggable["status"] == "UNKNOWN", untaggable
    assert untaggable["reason"] == "no_recognised_cash_concept_in_filing", untaggable

    # Amended filings are ignored rather than competing on filing date with the
    # original they restate.
    install(
        {
            TICKERS_URL: TICKER_MAP,
            submissions_url: submissions("Apple Inc.", 3571, "Electronic Computers"),
            facts_url: facts(
                Assets=usd(row("2025-09-27", 1_000.0), row("2026-09-27", 5.0, form="10-K/A", filed="2026-12-01")),
                CashAndCashEquivalentsAtCarryingValue=usd(row("2025-09-27", 10.0)),
            ),
        }
    )
    assert sec_edgar_screen.check_us_symbol("AAPL")["report_date"] == "2025-09-27"

    # ------------------------------------------------- drop-in compatibility
    # agents/shariah_agent._evaluate_us reads exactly these fields off the result and
    # treats anything other than COMPLIANT as REJECT. Every branch above must carry
    # a status and a symbol, and any non-COMPLIANT one must explain itself.
    install(clean)
    for result in (passing, bank, missing, untaggable, throttled, cash_rich):
        assert set(result) >= {"status", "symbol"}, result
        assert result["status"] in {"COMPLIANT", "NON_COMPLIANT", "UNKNOWN", "ERROR"}, result
        if result["status"] != "COMPLIANT":
            assert result.get("reason"), result

    # Every screen that produces a verdict must also log it -- one screen in,
    # one audit row out, whichever of the six exits it took.
    install(clean)
    logged = sec_edgar_screen.check_us_symbol("AAPL")
    assert RECORDED == [logged], RECORDED
    assert RECORDED[0]["status"] == "COMPLIANT", RECORDED

    # A failing log write is not allowed to cost us the verdict. This is the one
    # place in the repo where swallowing an exception is correct: the audit log
    # observes decisions, it does not make them.
    def explode(_verdict):
        raise sqlite3.OperationalError("database is locked")

    install(clean)
    sec_edgar_screen._record_screen = explode
    assert sec_edgar_screen.check_us_symbol("AAPL")["status"] == "COMPLIANT"

    print("PASS: sec_edgar_screen applies the SC two-tier screen and fails closed on missing data.")


if __name__ == "__main__":
    main()
