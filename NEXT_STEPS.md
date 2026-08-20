# Amanah Trader — Current State and Next Steps

Last updated: August 20, 2026 (Asia/Kuala_Lumpur).

Read `CLAUDE.md` for architecture and safety rules. This file is the running status: what
works, what doesn't, and what to do next.

## Where the project is

Amanah Trader is a local-first Shariah-compliant paper-trading control system on **Alpaca**.
The broker adapter, market data, gate chain, approval flow, real Shariah screening, and option
strike selection are all built and tested. **One trade has run end to end against the real
broker** — see the evidence trail below.

Current mode:

- `TRADING_MODE=approval` — human approval required for every order
- `PAPER_EXECUTION_ADAPTER=alpaca_mcp`
- `PAPER_EXECUTION_ENABLED=true` — **the system is armed**; broker submission is possible
- Live trading disabled by construction (`ALPACA_MODE=paper`, hardcoded paper base URL)

Alpaca paper account in use: suffix `0TCX`, **`CASH`** (`multiplier: 1`, `shorting_enabled:
false`), options trading level 3. This is the *test* account, not the dedicated hackathon one.

## ✅ Resolved: the margin-account blocker

`account_shariah_gate` rejected the paper account outright because it was `MARGIN`, so every
order — including plain equity — returned `margin_account_not_permitted`. Resolved on
2026-08-19 **without touching the gate**.

Alpaca offers no cash accounts ("No, we do not offer cash accounts. All accounts are set up as
margin accounts" — <https://alpaca.markets/support/alpaca-cash-accounts>), so the preferred
remedy did not exist. `backend/provision_cash_account.py --no-shorting --apply` instead reduced
the account to a cash-equivalent posture:

| field | before | after |
|---|---|---|
| `multiplier` | 4 | 1 |
| `buying_power` | 400000 | 100000 (== settled `cash`) |
| `shorting_enabled` | true | false |
| `check_alpaca_status` | `MARGIN` | `CASH` |
| `account_shariah_gate` | `REJECT` | `PASS cash_account_no_margin_exposure` |

`account_shariah_gate` and `account_type_from_multiplier` are byte-for-byte unchanged; the
latter already mapped `multiplier <= 1` to `CASH` and predates this problem. The account moved
to satisfy the gate, not the reverse. `provision_cash_account.py` is one-directional by
construction — it refuses to raise the multiplier or re-enable shorting.

The reasoning, **and the argument against it at equal length**, is recorded in
`docs/shariah-policy/margin-account-policy.md`, status *pending scholar review*. The honest
claim is "no margin capability is extended to this account", **not** "this is a cash account" —
it remains contractually a margin account and the 1x cap is revocable. Submission copy and demo
narration must not overstate it. `local_api.broker_account_context` re-reads `multiplier` from
the live account on every approval, so if the cap were raised the gate would resume rejecting
immediately.

## What works

**End-to-end live trade — proven once** *(2026-08-19, test account `0TCX`)*

A real order went preview → approval → `EXECUTE PAPER` → fill → reconcile → ledger against
`https://paper-api.alpaca.markets` over the `alpaca_mcp` transport, nothing mocked. Order
`bc939dcd-edfd-428f-9227-272d2521300f` (`client_order_id amanah-queue-5`, queue 5) filled
1 CVX at **206.89** against a **207.60** limit, and booked as `quantity 1.0, average_cost
206.89, cost_basis 206.89, realized_pnl 0.0, account_suffix 0TCX, account_type CASH`.

Verified three ways — local ledger, the broker's own `avg_entry_price`, and the order's
`filled_avg_price` all read 206.89. The agreement is meaningful because fill and limit
differed: `sync_filled_order` computes `float(dealt_avg_price or price)`, and `0.0` being
falsy means a null fill price would have silently booked the *limit* and looked plausible.
A second reconcile returned `ALREADY_SYNCED` with quantity still 1.0.

| evidence file | what it shows |
|---|---|
| `docs/live-trade-evidence/before-CVX.json` | the gate refusing a real order — `REJECT margin_account_not_permitted` while the account was still `MARGIN` |
| `docs/live-trade-evidence/after-CVX.json` | first real broker submission after the account fix |
| `docs/live-trade-evidence/reconciled-CVX.json` | the fill reconciled into the ledger, `outcome: VERIFIED`, `problems: []` |

The `before` file is worth keeping for the demo: it is the gate blocking a real order on a real
broker for a stated fiqh reason, which is the project's whole thesis in one artefact.

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
  FastAPI app with only the network seam mocked. Writing it found and fixed three real bugs,
  all the same shape — an equity-only rule applied to options: a
  side restriction that made both Level 1 strategies unreachable from `/paper/preview`; a
  required BUY quant signal, which refused a fully-collateralized cash-secured put on a
  Shariah-PASS underlying for `quant_no_buy_signal` alone (fixed 2026-08-20); and a
  portfolio-overlay unit mismatch that treated contracts/premium as shares/share-price.
- **What that test does not cover:** it sends `test_fixture: true`, so `paper_test_overrides`
  in `local_api.py` supplies the company verdict as `provider: PAPER_TEST_FIXTURE` and the
  Shariah screen is never invoked (verified: zero calls). The option-structure and account
  gates *are* exercised; the company screen is not. That hook is gated on paper mode, approval
  mode, execution enabled, and a whitelisted symbol, so it cannot fire in normal operation —
  but "end to end" should be read as covering order mechanics, not company screening.

  The same hook also injected a `quant_override` of `signal: "BUY"`, which hid a real bug for
  as long as the suite existed: `evaluate_candidate` required a BUY quant signal for *every*
  order, so a fully-collateralized cash-secured put on a Shariah-PASS underlying was refused
  for `quant_no_buy_signal` alone. Fixed 2026-08-20 by scoping that filter to non-option
  orders. Scenario 5 now narrows the fixture to the Shariah verdict only and swaps
  `agent_coordinator.evaluate_quant` for a real `NO_SIGNAL`, so the quant path is no longer
  masked.

**Integrity fixes**

- Option fills no longer corrupt the equity ledger (they previously booked contracts as shares
  of the underlying at 1/100th the true exposure)
- Reduce-only SELL guards at execution time and at portfolio sync time
- Approval-payload audit rejects malformed or stale payloads before any broker call

**Repo hygiene**

- Runs from a clean clone with no `.env` and no private vault
- `.env` has never been committed; `backend/.env.example` documents every variable

## What is broken or missing

**1. Screening is live, but every call is uncached and unthrottled.**
`agents/shariah_agent.py` routes the US path to `sec_edgar_screen.check_us_symbol`, reporting
`provider: SEC_EDGAR`. A screen is a live SEC fetch of up to ~4.7 MB taking ~0.7–2 s, and
`/paper/preview`, `/stock/{symbol}/profile` and `/stock/{symbol}/explain` all pay it on every
call. `sec_request` has no throttle at all, against SEC guidance of ~10 req/s. This is the
single strongest argument for building the screening store next, and it is now the largest
open backend item.

*(The second Zoya screening path is closed: `us_strategy.py` and `explain_compliance.py` both
route through the one entry point, and `test_single_screening_path.py` enforces it with a
static AST import check so a new parallel path fails a test the moment it is written.)*

**2. Held positions are never re-screened.**
Every screening call site is on the *order* path. `portfolio_store.py` contains no reference to
compliance at all — the system screens at the moment you buy and then never looks again. This
is what the screening store below is for.

**3. Options P&L is not tracked locally.**
`portfolio_store` models whole shares only. Option fills are audited under their OCC symbol but
create no position. Alpaca is the source of truth. Deliberate scope decision, not a defect.

**4. No *option* order has run end to end live.**
The proven live trade was plain equity. Both Level 1 structures are exercised only by
`test_option_execution_smoke.py` against a mocked `alpaca_request` seam. Since options are the
hackathon's stated differentiator, one real covered call or cash-secured put through the full
chain is worth more than any further equity trade.

**5. The proven trade lives in a database no deployment can see.**
`backend/*.db` is gitignored by design, so the CVX position sits only in the
`.worktrees/live-trade-backend` SQLite file. The deployed Replit instance has its own empty
database. Any trade meant to appear in the demo must be run **against the deployed instance**,
not locally. Easy to hit twice; see the demo-trade step below.

**6. The margin fix is pending scholar review.**
`docs/shariah-policy/margin-account-policy.md` records a decision, not a settled ruling. It is
the one compliance claim in the project that a knowledgeable judge could reasonably contest.

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

**38 suites pass.** There are 39 `test_*.py` files in `backend/`; `test_moomoo.py` is the one
excluded, and it hangs by design — it drives the moomoo SDK directly to verify a *real* OpenD
connection, bypassing the `check_moomoo_status()` TCP pre-check that makes every other suite
fail fast without a gateway running. `CLAUDE.md` lists all 38 explicitly.

```powershell
.\.venv\Scripts\python.exe backend\test_sec_edgar_screen.py
.\.venv\Scripts\python.exe backend\test_option_execution_smoke.py
.\.venv\Scripts\python.exe backend\test_single_screening_path.py
.\.venv\Scripts\python.exe backend\test_repo_defaults.py
```

`test_local_api_smoke.py` used to be listed here as an environmental failure. It is not — it
passes, and has since the Moomoo TCP pre-check landed.

**Convention worth keeping:** when a new test passes on the first run, break the code
deliberately and confirm it fails. Every suite added recently was mutation-checked that way —
3 mutations against the quant-agent provider switch, 5 against the `/explain` contract, 6
against the strategy endpoint, 2 against the single-screening-path check, all caught.

## Next steps, in order

1. **Build the screening store.** Approach A above: an EDGAR raw-response cache keyed by CIK,
   an append-only `shariah_screens` table, and a throttle on `sec_request`. Answer the three
   open questions first (purification scope, re-screen trigger, cache TTL). This is the largest
   genuinely open backend item, and every call to `/explain` currently pays for its absence.
2. **Run the submission demo trade on the dedicated hackathon account, through the deployed
   Replit instance.** Not locally — see broken/missing #5. Provision the account, confirm
   `check_alpaca_status` reports `CASH` (apply `provision_cash_account.py` if it does not), then
   drive preview → approval → `EXECUTE PAPER` → reconcile against the deployment so its own
   database captures the position.
3. **Get one Level 1 option order through the live chain** — a covered call needs 100 shares of
   a Shariah-PASS underlying, a cash-secured put needs settled collateral. Options are the
   stated differentiator and are the least-proven part of the system.
4. **Get the margin-account policy in front of a scholar**, or state plainly in the submission
   that it is unreviewed. It is the most contestable compliance claim in the project.
5. **Upgrade the fiqh citations from secondary to primary sources.** `shariah_explain.py`
   already labels each citation `regulatory_methodology` or `secondary_summary`, so the gap is
   visible in the payload; research notes live under `hackathon/alpaca-2026/research/`.
6. **Then, and only then, the deferred surfaces:** the position lifecycle view and the
   pre-purchase research view, both of which are views over the store from step 1.

Completed since the last revision, no longer listed above: the margin-account blocker, the
first end-to-end live trade, `GET /stock/{symbol}/explain`, `GET /stock/{symbol}/option-strategy`,
the duplicate Zoya screening path, demo hosting on Replit, and the stale Moomoo-era position
(cleared; backup at `backend/paper_trading.db.bak-stale-aapl-cleanup`).

## Standing constraints

- Do not move to `autonomous_paper` until manual paper execution is reliable and fully audited.
- Do not put an LLM in the decision path. A model may explain a gate decision; it must never
  make, approve, or bypass one. The 8-K agent above is a flagger, and that boundary is what
  keeps it acceptable.
- Do not weaken a gate to unblock a demo. If a gate is inconvenient, that is the gate working.
- Treat FinceptTerminal as architectural inspiration only — it is AGPL-3.0 plus a commercial
  license, so do not copy code, assets, prompts, or screens without a license review.
