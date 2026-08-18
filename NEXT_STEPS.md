# Amanah Trader — Current State and Next Steps

Last updated: August 18, 2026 (Asia/Kuala_Lumpur).

Read `CLAUDE.md` for architecture and safety rules. This file is the running status: what
works, what doesn't, and what to do next.

## Where the project is

Amanah Trader is a local-first Shariah-compliant paper-trading control system on **Alpaca**.
The broker adapter, market data, gate chain, and approval flow are built and tested. The
compliance data feeding the gates is not yet real, and no trade has run end to end.

Current mode:

- `TRADING_MODE=approval` — human approval required for every order
- `PAPER_EXECUTION_ADAPTER=alpaca_mcp`
- `PAPER_EXECUTION_ENABLED=true` — **the system is armed**; broker submission is possible
- Live trading disabled by construction (`ALPACA_MODE=paper`, hardcoded paper base URL)

Alpaca paper account in use: suffix `0TCX`, `MARGIN`, options trading level 3.

## What works

**Broker adapter** — `alpaca_paper_adapter.py`

- Equity and Level 1 option orders (sell covered call, sell cash-secured put, and closing them)
- Two transports: REST (`alpaca`) and the official MCP server (`alpaca_mcp`)
- MCP verified live: handshake, tool schemas, and the `_alpaca_mcp_security` trust envelope
- Paper-only by construction; multi-leg spreads rejected by design

**Market data** — `alpaca_market_data.py`

- Drop-in replacement for the Tiingo path; provider selected by `MARKET_DATA_PROVIDER`
- Verified live: 252 daily bars for AAPL, 316 Sep-2026 option contracts with live quotes
- Automatic IEX fallback when the plan cannot query recent SIP data
- Tiingo retained as a working fallback provider

**Gate chain** — merged from `feature/shariah-options-gate`

- `shariah_gate` (company), `option_structure_gate` (contract), `account_shariah_gate` (Riba)
- Single entry point: `shariah_candidate.build_shariah_candidate()`
- Wired into `POST /paper/approval`; a covered call on a MARGIN account is now rejected with
  `margin_account_not_permitted`, and an under-collateralized put with
  `option_structure_rejected`

**Integrity fixes**

- Option fills no longer corrupt the equity ledger (they previously booked contracts as shares
  of the underlying at 1/100th the true exposure)
- Reduce-only SELL guards at execution time and at portfolio sync time
- Approval-payload audit rejects malformed or stale payloads before any broker call

**Repo hygiene**

- Runs from a clean clone with no `.env` and no private vault: Shariah universe and policy
  notes resolve to committed in-repo copies (`data/`, `docs/`)
- `.env` has never been committed; `backend/.env.example` documents every variable

## What is broken or missing

**1. Shariah screening is running on fake data — blocks everything.**
`ZOYA_ENVIRONMENT=sandbox` returns randomized results: JPM and BAC screen `COMPLIANT`, AAPL and
KO screen `NON_COMPLIANT`. Until this is real, every gate decision is meaningless. Decision
taken: build an AAOIFI screen from free SEC EDGAR XBRL data rather than paying for Zoya live.
Verified feasible — EDGAR exposes the ticker→CIK map and current-quarter fundamentals with no
API key. Note that the **business-activity screen must run first**: on financial ratios alone,
JPMorgan passes. SIC 6021 is what disqualifies it.

**2. No trade has ever run end to end.**
Preview → Shariah → risk → approval → `EXECUTE PAPER` → Alpaca → fill → reconcile → ledger has
never been exercised against the real API. This is the largest unquantified risk.

**3. No strategy layer.**
Nothing calls `fetch_option_chain` to pick a strike. Option chain data is available; the
selection logic is not written.

**4. Options P&L is not tracked locally.**
`portfolio_store` models whole shares only. Option fills are audited under their OCC symbol but
create no position. Alpaca is the source of truth for options P&L. Deliberate scope decision.

**5. `/explain` endpoint not built.**
`explain_compliance.py` exists as a CLI that combines a screening result with local policy
notes, under the rule that notes explain but never override. It is not exposed over HTTP or in
the dashboard.

## Running it

From the repo root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn local_api:app --app-dir backend --host 127.0.0.1 --port 8000
```

Dashboard: open `dashboard\index.html`.

Check configuration without printing secrets:

```powershell
.\.venv\Scripts\python.exe backend\check_config.py
```

Expected: `Alpaca mode: paper`, both Alpaca keys `True`, adapter `alpaca_mcp`.

## Tests

27 suites pass. Run any of them directly, e.g.:

```powershell
.\.venv\Scripts\python.exe backend\test_alpaca_shariah_wiring.py
.\.venv\Scripts\python.exe backend\test_alpaca_paper_adapter.py
.\.venv\Scripts\python.exe backend\test_option_fill_ledger.py
.\.venv\Scripts\python.exe backend\test_repo_defaults.py
```

Two suites fail for environmental reasons only, not regressions: `test_moomoo.py` and
`test_local_api_smoke.py` both try to reach Moomoo OpenD on `127.0.0.1:11111`, which is not
running. `test_local_api_smoke.py` hangs on the SDK's retry loop rather than failing fast.

## Next steps, in order

1. **Build the AAOIFI screen.** `sec_fundamentals.py` (ticker→CIK, companyfacts, SIC) feeding
   `aaoifi_screen.py` (business-activity screen first, then ratios). Scope it to a 20–40 symbol
   watchlist, not the whole market — a screen that shows its evidence beats a screen with
   breadth. Use `docs/shariah-policy/screening-criteria-breakdown.md` as the spec; never invent
   a threshold.
2. **Get one trade through end to end.** Any compliant symbol, one share, full chain. Do this
   before anything depends on it working.
3. **Solve demo hosting.** Submission requires the demo on Streamlit, Replit, or Vercel. The
   current dashboard is a local static file against a local FastAPI backend. Prove the deploy
   path early with a stub.
4. **Covered-call selection** on top of `fetch_option_chain`.
5. **`GET /stock/{symbol}/explain`** plus a dashboard panel showing verdict → rule fired →
   fiqh basis with citation.
6. **Clear the stale Moomoo-era position** before demoing the portfolio view:
   `4.0 AAPL` at average cost `323.3487`, account suffix `1740`, in `backend/paper_trading.db`.
   It predates the Alpaca account (`0TCX`) and will pollute exposure math in the demo.

## Read-only API contracts available for UI work

Use these rather than rebuilding aggregates in the browser:

| Endpoint | Purpose |
|---|---|
| `GET /market-overview` | Watchlist health, scan freshness, data-source counts |
| `GET /investment-committee` | Candidates, committee status, pending approvals, exposure |
| `GET /stock/{symbol}/profile` | Shariah status, market data, latest scan, exposure, limits |
| `GET /positions` | Flattened positions with valuation and reduce eligibility |
| `GET /execution-audit` | Queue integrity, broker safety, payload audit failures |
| `GET /portfolio` | Positions, fills, cost basis, realized P&L, exposure percentages |

## Standing constraints

- Do not move to `autonomous_paper` until manual paper execution is reliable and fully audited.
- Do not put an LLM in the decision path. A model may explain a gate decision; it must never
  make, approve, or bypass one.
- Treat FinceptTerminal as architectural inspiration only — it is AGPL-3.0 plus a commercial
  license, so do not copy code, assets, prompts, or screens without a license review.
