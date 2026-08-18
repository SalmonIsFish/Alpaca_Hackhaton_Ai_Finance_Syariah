# Amanah Trader — Current State and Next Steps

Last updated: August 19, 2026 (Asia/Kuala_Lumpur).

Read `CLAUDE.md` for architecture and safety rules. This file is the running status: what
works, what doesn't, and what to do next.

## Where the project is

Amanah Trader is a local-first Shariah-compliant paper-trading control system on **Alpaca**.
The broker adapter, market data, gate chain, approval flow, real Shariah screening, and option
strike selection are all built and tested. No trade has run end to end against the real broker.

Current mode:

- `TRADING_MODE=approval` — human approval required for every order
- `PAPER_EXECUTION_ADAPTER=alpaca_mcp`
- `PAPER_EXECUTION_ENABLED=true` — **the system is armed**; broker submission is possible
- Live trading disabled by construction (`ALPACA_MODE=paper`, hardcoded paper base URL)

Alpaca paper account in use: suffix `0TCX`, `MARGIN`, options trading level 3.

## ⚠ Blocker to resolve before any live demo

**The configured paper account is `MARGIN`, and `account_shariah_gate` rejects margin accounts
outright — for every order, including plain equity.** The gate is doing exactly what it was
designed to do: *"carrying margin capability at all is a standing Riba exposure regardless of
whether a given order draws on it."* But it means that on account `0TCX`, every approval
returns `margin_account_not_permitted` and nothing can ever be traded.

This has not been hit yet only because no trade has run end to end. It will be the first thing
that happens when one does. Options are:

1. Provision an Alpaca paper account configured as **CASH** and point `.env` at it. Preferred —
   it satisfies the gate honestly, and a cash account is what the whole design assumes.
2. Confirm whether Alpaca even offers a cash paper account. If it does not, this needs a
   documented, scholar-reviewable decision about what `account_type` the system should treat a
   paper margin account as — **not** a code change that weakens the gate.

Do not "fix" this by relaxing `account_shariah_gate`. Verify the live account type first with
`check_config.py` / `check_alpaca_status`; the `MARGIN` value above comes from this document,
not from a fresh check.

## What works

**Shariah screening — real data** — `sec_edgar_screen.py` *(new, this session)*

- Self-built two-tier screen off free SEC EDGAR filings; no API key, no vendor.
- Tier 1 business activity by SIC code, short-circuiting before any ratio is fetched. Tier 2
  interest-bearing debt / total assets and conventional cash / total assets, each strictly
  under 33%.
- Ratios anchor on the **latest annual** filing, and every component must be tagged at that
  exact balance-sheet date — components are never borrowed across periods.
- Fails closed: unmapped ticker, fetch error, missing annual anchor, or an unrecognisable cash
  tag all return UNKNOWN/ERROR rather than a guessed COMPLIANT.
- Live results: AAPL COMPLIANT (debt 27.5%, cash 15.2%), JPM NON_COMPLIANT (SIC 6021), KO
  NON_COMPLIANT (debt 40.2%), MO NON_COMPLIANT (SIC 2111), MSFT COMPLIANT, TSLA COMPLIANT but
  at 32.0% cash — one point from failing.

  **Naming note:** earlier plans called this "the AAOIFI screen". What is implemented is the
  **SC Malaysia / SAC** methodology, because that is what
  `docs/shariah-policy/screening-criteria-breakdown.md` actually specifies. They are different
  standards — AAOIFI ratios are denominated on market capitalisation, SC on total assets. The
  doc was followed; the old name was wrong.

**Option strike selection** — `option_strategy.py` *(new, this session)*

- Covered call and cash-secured put, both Level 1, both sell-to-open.
- Rule: 1–7 DTE, then the strike closest to **4% OTM inside a 2–7% band**, filtered for a live
  bid, spread ≤15% of mid, a minimum premium, and a standard 100-share multiplier. Sized from
  owned shares or settled cash; walks down the ranking when the top strike cannot be secured.
- Emits an `option_contract` that drops straight into `build_shariah_candidate`, plus a
  `rationale` string narrating the choice for the demo.
- No Greeks are available on this Alpaca tier, which is why the rule is moneyness-based rather
  than delta-based. A fixed band is also reproducible where a delta surface would not be.
- `check_option_strategy.py` drives it live from the CLI without touching `local_api.py`.

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

**Gate chain**

- `shariah_gate` (company), `option_structure_gate` (contract), `account_shariah_gate` (Riba)
- Single entry point: `shariah_candidate.build_shariah_candidate()`
- `test_option_execution_smoke.py` exercises preview → approval → execute through the real
  FastAPI app with only the network seam mocked. Writing it found and fixed two real bugs: a
  side restriction that made both Level 1 strategies unreachable from `/paper/preview`, and a
  portfolio-overlay unit mismatch that treated contracts/premium as shares/share-price.

**Integrity fixes**

- Option fills no longer corrupt the equity ledger (they previously booked contracts as shares
  of the underlying at 1/100th the true exposure)
- Reduce-only SELL guards at execution time and at portfolio sync time
- Approval-payload audit rejects malformed or stale payloads before any broker call

**Repo hygiene**

- Runs from a clean clone with no `.env` and no private vault
- `.env` has never been committed; `backend/.env.example` documents every variable

## What is broken or missing

**1. The new screen is built but not routed.**
`agents/shariah_agent.py` still imports `zoya_compliance.check_us_symbol`. The swap to
`sec_edgar_screen.check_us_symbol` is a one-line change and the return shapes are compatible,
but until it happens every gate decision is still running on randomized sandbox data. **This is
the single highest-value line of code outstanding.**

**2. The strategy layer has no endpoint.**
`option_strategy.py` works and is tested, but nothing calls it over HTTP. A caller must supply
`option_contract` to `/paper/preview` by hand, or use `check_option_strategy.py`.
`local_api.py` was deliberately left untouched to avoid collisions.

**3. No trade has ever run end to end.**
Preview → Shariah → risk → approval → `EXECUTE PAPER` → Alpaca → fill → reconcile → ledger has
never been exercised against the real API. Largest unquantified risk. See the margin blocker
above — this is what will surface it.

**4. Held positions are never re-screened.**
Every screening call site is on the *order* path. `portfolio_store.py` contains no reference to
compliance at all. The system screens at the moment you buy and then never looks again. This is
the subject of the next session — see below.

**5. Options P&L is not tracked locally.**
`portfolio_store` models whole shares only. Option fills are audited under their OCC symbol but
create no position. Alpaca is the source of truth. Deliberate scope decision.

**6. `/explain` endpoint not built.**
`explain_compliance.py` exists as a CLI combining a screening result with local policy notes,
under the rule that notes explain but never override. Not exposed over HTTP or in the dashboard.

**7. Demo hosting unsolved.**
Submission requires the demo on Streamlit, Replit, or Vercel. The current dashboard is a local
static file against a local FastAPI backend.

**8. Stale Moomoo-era position.**
`4.0 AAPL` at average cost `323.3487`, account suffix `1740`, in `backend/paper_trading.db`. It
predates the Alpaca account and will pollute exposure math in the demo.

## Next session — time-varying compliance

The idea driving this: a company that screens compliant today can stop being compliant later —
a new contract, a change in the business, a balance sheet that drifts over the 33% line. The
current system cannot see any of that.

This is **not** a new requirement. `screening-criteria-breakdown.md` §2 already specifies it,
under *"Shariah-compliant securities which are subsequently re-classified as Shariah
non-compliant"*, along with the disposal rules and a twice-yearly review cycle (last Friday of
May and November). It is a documented gap, not a feature invention.

### Agreed so far

- **The colours describe the position, not permission to buy.** The buy gate stays exactly as
  it is — binary, fail-closed, untouched. Green/yellow/red answers *"what must I do about what
  I already hold?"*, which the system currently cannot answer at all.

  | | meaning | action |
  |---|---|---|
  | 🟢 | screens compliant, comfortable margin | none |
  | 🟡 | still compliant, but thin margin or stale/weak data (TSLA at 32.0% cash) | watch |
  | 🔴 | screen has flipped to non-compliant | **required**: dispose or hold-under-exemption; purification accruing |

- **Red always carries a required action**, never a vague warning. This is what keeps "yellow
  means trade it anyway" from creeping in and turning a hard gate into a soft one.
- The SC disposal rules are a **state machine pivoting on an effective date**, not a score:
  price ≥ cost on the effective date → must dispose; price < cost → may hold until dividends +
  market value reach cost; dividends/gains before the effective date → keep; after it → owed to
  baitulmal/charity.
- **Both surfaces are in scope**: the position lifecycle above, *and* a pre-purchase research
  view for companies you do not own yet. Its universe is the watchlist, pre-warmed on a
  schedule, **plus** on-demand lookup of any US ticker.

- **Build the screening store first; both surfaces are views over it.** This replaces the
  earlier plan of building re-screening as a feature in its own right. The two surfaces need
  the same expensive artefact — run the screen over a set of symbols, cache it, keep it dated —
  so it is built once:

  | from the store | feeds |
  |---|---|
  | latest verdict + evidence | pre-purchase research view |
  | verdict changed vs. the previous run | re-screen alert, and the **effective date** |
  | margin to the 33% line | the colour, on both surfaces |

- **Storage: two layers** (approach A of three considered).
  1. **Raw EDGAR cache** — the `companyfacts` payload per CIK on disk with a TTL, mirroring
     `market_data_cache/`. Measured: **3.61 MB for AAPL, 4.66 MB for MSFT**, so a 30-symbol
     daily sweep would re-download well over 100 MB of data that only changes when a filing
     lands, i.e. quarterly. This layer exists solely to avoid re-fetching.
  2. **`shariah_screens` table** in `paper_trading.db`, **append-only** — symbol, screened_at,
     status, deciding tier, report_date, both ratios, evidence JSON. Follows the existing
     `ensure_*_tables` / `CREATE TABLE IF NOT EXISTS` pattern in `portfolio_store.py` and
     `watchlist_store.py`.

  Append-only rather than overwrite-in-place because re-screening must detect *change*, which
  needs the previous verdict to compare against — and that comparison is exactly what produces
  the effective date. SQLite rather than JSON-per-symbol because the position lifecycle is a
  **join**: *"which symbols do I hold whose latest verdict just flipped?"* Positions already
  live in that database.

  Rejected: a file-based store matching `market_data_cache` (every cross-symbol question becomes
  a full scan, and a sweep has no transaction protecting concurrent writes), and re-fetching on
  every sweep (wasteful against data that changes quarterly).

### Constraints to hold to

1. **One screening record, two views — never two screening paths.** If browsing and re-screening
   each invoke the screen their own way they will eventually disagree about the same company,
   with no way to tell which is right.
2. **The pre-purchase colour must never imply permission.** A non-compliant company is not "red
   because risky" — it is not buyable, and the gate says so regardless of colour. That surface
   needs the binary verdict as its primary badge, colour strictly secondary.
3. **Do not use one traffic light for two meanings.** Pre-purchase yellow would mean "thin
   evidence"; position yellow means "watch this". Same dot, different claim — that is how
   "yellow means trade it anyway" gets back in. Preference: reserve traffic lights for
   *required action* only, and let the research view show the actual margin and evidence, which
   `sec_edgar_screen` already returns. A colour compresses evidence into a dot, and this
   project's thesis is that it *proves* rather than asserts.

### Open questions — resolve these before designing

1. **Is purification tracking in scope?** Smaller than first assessed: `paper_positions` already
   carries `average_cost` and `cost_basis`, so the missing input is **dividend history**, not
   cost basis. Still the biggest scope fork, and probably where the judging marks are, since
   almost nothing on the market implements it.
2. **What triggers a re-screen?** SC says twice yearly, which is too slow to demo. Likely
   on-demand plus a daily sweep, but the *effective date* semantics need pinning down: the date
   SC would have reclassified, or the date we noticed?
3. **What is the raw cache TTL, and what invalidates it?** A flat 24h is simplest; checking the
   `submissions` endpoint for a newer filing is more correct and costs one small request.

### Known gap to fix as part of this

`sec_request` has **no throttle**. SEC's guidance is a maximum of 10 requests/second and
reasonable use overall. A watchlist sweep is the first thing that will make sustained requests,
so the throttle belongs with this work — a robustness and politeness fix, not an optimisation.

### Sketched, deliberately not designed yet

- **Explainer chatbot.** Lowest risk of the four — `CLAUDE.md` already permits a model to
  explain a decision, and `explain_compliance.py` already does this deterministically with the
  rule *"notes explain but cannot override."* A chat surface over the trace is an extension of
  an existing principle, not a new one. Good demo value, roughly a day.
- **8-K event detection agent.** An agent reading SEC **material-event filings** — primary
  sources, not news sentiment — that *flags* companies for re-screening. Produces **evidence,
  never verdicts**; the deterministic screen still decides. This is the only way to catch a
  business-activity change such as a new defense contract, which the SIC-based tier 1 will
  never see, since SIC is one primary-industry label that rarely changes. Highest cost and the
  only one carrying philosophical risk — keep it strictly a flagger.

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

Screen a symbol against real SEC data, or select a contract, without creating an order:

```powershell
.\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'backend'); import sec_edgar_screen; print(sec_edgar_screen.check_us_symbol('AAPL'))"
.\.venv\Scripts\python.exe backend\check_option_strategy.py AAPL --shares 100
```

## Tests

30 suites pass. Run any of them directly, e.g.:

```powershell
.\.venv\Scripts\python.exe backend\test_sec_edgar_screen.py
.\.venv\Scripts\python.exe backend\test_option_strategy.py
.\.venv\Scripts\python.exe backend\test_option_execution_smoke.py
.\.venv\Scripts\python.exe backend\test_repo_defaults.py
```

Two suites fail for environmental reasons only, not regressions: `test_moomoo.py` and
`test_local_api_smoke.py` both try to reach Moomoo OpenD on `127.0.0.1:11111`, which is not
running. `test_local_api_smoke.py` hangs on the SDK's retry loop rather than failing fast.

**Convention worth keeping:** when a new test passes on the first run, break the code
deliberately and confirm it fails. The two suites added this session were each mutation-checked
that way — 7 mutations against the screen, 12 against the strategy layer, all caught.

## Next steps, in order

1. **Switch `agents/shariah_agent.py` to `sec_edgar_screen`.** One line. Until this lands, every
   gate decision still runs on randomized sandbox data.
2. **Resolve the margin-account blocker** above. Nothing can be approved until it is.
3. **Get one trade through end to end.** Any compliant symbol, one share, full chain. Do this
   before anything else depends on it working.
4. **Design the screening store** (approach A above) — answer the three open questions first.
   The store comes before either surface; re-screening and the research view are both views
   over it.
5. **Solve demo hosting.** Prove the deploy path early with a stub.
6. **Expose the strategy layer** over HTTP, and `GET /stock/{symbol}/explain` plus a dashboard
   panel showing verdict → rule fired → fiqh basis with citation.
7. **Clear the stale Moomoo-era position** before demoing the portfolio view.

## Standing constraints

- Do not move to `autonomous_paper` until manual paper execution is reliable and fully audited.
- Do not put an LLM in the decision path. A model may explain a gate decision; it must never
  make, approve, or bypass one. The 8-K agent above is a flagger, and that boundary is what
  keeps it acceptable.
- Do not weaken a gate to unblock a demo. If a gate is inconvenient, that is the gate working.
- Treat FinceptTerminal as architectural inspiration only — it is AGPL-3.0 plus a commercial
  license, so do not copy code, assets, prompts, or screens without a license review.
