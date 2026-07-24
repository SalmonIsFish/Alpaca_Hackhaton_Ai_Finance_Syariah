# Amanah Trader Handoff

## Resume After Shutdown

Last saved: July 23, 2026, Asia/Kuala_Lumpur.

What just worked:

- The controlled Moomoo paper execution flow worked end to end.
- Dashboard approval queue produced an `APPROVED_PAPER_READY` AAPL paper order.
- `Execute Paper` submitted to the Moomoo paper/simulate account.
- Moomoo Papertrade showed a transaction update that the paper order was filled.

Start next session:

```powershell
cd C:\Users\G2\OneDrive\Documents\Ai_Finance_Syariah\backend
.\run_local.ps1
```

Then open:

```text
C:\Users\G2\OneDrive\Documents\Ai_Finance_Syariah\dashboard\index.html
```

Recently completed build task:

1. Renamed queue label `Broker On` to `Broker Submitted`.
2. Added a clearer Paper Orders section with broker order id, submitted/fill status, environment, account suffix, execution timestamp, and raw adapter response.
3. Ran a controlled Moomoo paper execution test through the locked `/paper/execute/{queue_id}` path.
4. Added paper order reconciliation with `POST /paper/reconcile/{queue_id}` and dashboard `Refresh Status`.
5. Added local portfolio/exposure tracking from filled paper orders with `GET /portfolio`.
6. Added mark-to-market portfolio valuation using Tiingo/cache prices with no fixture fallback.
7. Keep FinceptTerminal as reference inspiration only; do not copy code/assets because of licensing constraints.

## Current State

Amanah Trader is currently a local-first, Shariah-aware paper trading control system with a multi-agent architecture.

Current mode:

- `TRADING_MODE=approval`
- `PAPER_EXECUTION_ENABLED=false`
- `PAPER_EXECUTION_ADAPTER=disabled`
- live trading disabled
- broker submission disabled until both the execution lock and adapter are enabled

Working components:

- Dashboard UI with dark/light mode.
- Local FastAPI backend.
- Agent coordinator.
- Shariah Agent with market routing:
  - numeric symbols route to Malaysia SC local universe
  - US symbols route to Zoya
- Quant Agent using Tiingo market data.
- Risk Engine with hard-coded limits.
- Approval queue in SQLite.
- Moomoo OpenD paper account status check.
- Opportunities scanner for Shariah/quant/risk watchlist review, including trend and breakout status.
  - scanner requires real Tiingo history
  - scanner shows `DATA_ERROR` instead of fixture prices when market data is unavailable
  - scanner shows alert candidates near breakout, but only `READY` candidates can be approved
  - dashboard can auto-scan the watchlist on a configurable minute interval
- Locked paper execution endpoint.
- Typed paper execution confirmation gate requiring `EXECUTE PAPER`.
- Paper execution gate stack with fake and real adapter paths:
  - `approval` or `autonomous_paper` trading mode required
  - `PAPER_EXECUTION_ENABLED=true` required
  - Shariah PASS required
  - Risk PASS required
  - active market-compatible SIMULATE account required
  - broker submission recorded in queue and audit when adapter submits
  - read-only reconciliation records submitted/filled/cancelled/rejected/expired status transitions
- Real Moomoo adapter is available with `PAPER_EXECUTION_ADAPTER=moomoo`, currently limited to US equity paper orders such as `AAPL` -> `US.AAPL`.
- Portfolio ledger stores filled paper orders as local positions:
  - positions include quantity, average cost, cost basis, realized P&L placeholder, account suffix/type, and update time
  - dashboard has a Portfolio/Risk section
  - market value, unrealized P&L, and exposure are priced from Tiingo/cache when available
  - valuation reports `DATA_ERROR` instead of using fixture prices when market data is unavailable

## How To Continue

Open PowerShell:

```powershell
cd C:\Users\G2\OneDrive\Documents\Ai_Finance_Syariah\backend
.\run_local.ps1
```

Leave that window open.

Open the dashboard:

```text
C:\Users\G2\OneDrive\Documents\Ai_Finance_Syariah\dashboard\index.html
```

Recommended test flow:

1. Refresh dashboard.
2. Confirm:
   - API Connection: connected
   - Trading Mode: paper / simulate
   - Operating Mode: approval
   - Paper Execution: locked
   - Moomoo OpenD: paper ready
3. Click Scan in Opportunities.
4. Review:
   - Ready count
   - Alert count
   - Shariah status
   - Quant signal
   - Risk status
   - trigger price
   - distance to trigger
   - breakout gap
5. Optionally enable Auto Scan and leave the dashboard open.
6. If a row is Ready, click Use In Ticket.
7. Run agents for that symbol.
8. Confirm:
   - Shariah Agent: PASS / US
   - Quant Agent: BUY
   - Risk Engine: PASS
   - Broker Submission: Disabled
9. If ready, approve the paper order.
10. Confirm it appears in Approval Queue.
11. Click Execute Paper.
12. Type `EXECUTE PAPER` when prompted.
13. Confirm result is `EXECUTION_LOCKED` while `PAPER_EXECUTION_ENABLED=false`.

## Useful Checks

```powershell
cd C:\Users\G2\OneDrive\Documents\Ai_Finance_Syariah\backend
..\.venv\Scripts\python.exe test_local_api_smoke.py
..\.venv\Scripts\python.exe test_paper_execution_gates.py
..\.venv\Scripts\python.exe test_moomoo_paper_adapter.py
..\.venv\Scripts\python.exe check_market_data.py AAPL --strict
..\.venv\Scripts\python.exe check_zoya.py AAPL
..\.venv\Scripts\python.exe check_moomoo_status.py
```

Expected good signs:

- smoke test passes
- paper execution gate test passes
- Moomoo adapter mapping test passes
- Tiingo source is `tiingo`
- Zoya status is `COMPLIANT` for AAPL
- Moomoo status is `paper_account_ready`

## Next Plan

Next recommended build step:

1. Tune portfolio/risk policy:
   - set `PAPER_ACCOUNT_EQUITY` to the intended paper account risk base
   - decide whether same-symbol add-ons should always block or only block above the 5% position ceiling
   - consider per-symbol overrides for highly liquid names if needed
   - keep pricing read-only and order placement behind the existing gates
   - Risk Policy panel now displays the active denominator, limits, current exposure, add-on policy, and current ticket pass/block state
   - Portfolio rows now include a `Reduce` action that fills the ticket as a reduce-only SELL preview
   - risk thresholds are now configurable with `MAX_POSITION_PCT`, `MAX_TOTAL_EXPOSURE_PCT`, `MAX_LOSS_PER_TRADE_PCT`, `MAX_DAILY_LOSS_PCT`, and `MAX_ORDERS_PER_DAY`

2. After portfolio/risk limits are reliable, add market/investment-firm features:
   - watchlist
   - opportunities page
   - stock profile page
   - market overview
   - portfolio/exposure view
   - investment committee review page

Do not jump to autonomous paper mode until manual paper execution is reliable and fully audited.

## Latest Operator Notes

- Portfolio-derived risk limits were added on July 25, 2026:
  - `PAPER_ACCOUNT_EQUITY` defaults to `10000` and is used as the denominator for position and total exposure percentages.
  - `GET /portfolio` now returns account exposure percentages and risk limits.
  - `/agent/evaluate` and `/paper/preview` add a portfolio risk overlay using market value when available, otherwise cost basis.
  - approvals are blocked for projected position exposure above 5%, projected total exposure above 25%, or same-symbol buy add-ons.
  - Dashboard order ticket exposure fields are pre-filled from current portfolio exposure.
  - Investment Committee and Approval Queue show portfolio exposure blockers.
- Risk usability and reduce-position handling were added on July 25, 2026:
  - previews now include `blocker_messages` with readable explanations for quant and portfolio blockers.
  - SELL previews are reduce-only and can become `READY_FOR_APPROVAL` when a local position exists and the sell quantity does not exceed local quantity.
  - full-position SELL projections now reduce position and total exposure to zero.
  - Dashboard exposure inputs accept two decimal places such as `3.22`.
  - Dashboard Risk Policy panel shows account equity, risk limits, current exposure, same-symbol add-on policy, and current ticket state.
  - Portfolio `Reduce` buttons populate a SELL ticket from the local position.
  - `CLAUDE.md` was added as the Claude Code handoff file.
- Configurable risk limits were added on July 25, 2026:
  - `risk_checks.py` keeps current defaults but accepts injected limits.
  - `load_settings()` reads all risk thresholds from env vars.
  - `/portfolio` and portfolio risk overlays report/use the active configured limits.
- SELL/reduce technical coverage was added on July 25, 2026:
  - portfolio tests now verify partial SELL realized P&L and full-close realized P&L.
  - closed positions no longer hide realized P&L from `total_realized_pnl`.
  - Moomoo adapter tests verify SELL maps to `TrdSide.SELL` without contacting OpenD.
- Pre-trade quote snapshots were added on July 25, 2026:
  - `/paper/preview` now records `quote_snapshot` with latest close, price date, source, freshness/cache fields, and bar count.
  - approval queue payloads persist the quote snapshot for audit.
  - dashboard Approval Queue and Paper Orders show preview quote metadata.
- Execution-time reduce-only SELL guard was added on July 25, 2026:
  - `/paper/execute/{queue_id}` now re-checks local portfolio quantity before submitting any SELL.
  - SELL is rejected with `PORTFOLIO_SELL_GATE_FAILED` if no local position exists or requested quantity exceeds the active paper account suffix.
  - Tests cover no-position SELL, oversized SELL, and valid reduce SELL without contacting Moomoo.
- Portfolio fill sync SELL integrity was added on July 25, 2026:
  - filled SELL reconciliations are rejected with `INVALID_SELL_FILL` when local holdings are missing or smaller than the fill quantity.
  - rejected SELL fills are not inserted into `paper_fills` and do not change `paper_positions`.
  - tests cover no-position and oversized SELL reconciliation before any ledger mutation.
- Stock profile backend contract was added on July 25, 2026:
  - `GET /stock/{symbol}/profile` combines Shariah status, market data, latest opportunity scan result, local portfolio exposure, and active risk limits.
  - this is a read-only API intended to support a future Claude Code stock detail page without changing broker or execution behavior.
  - `test_stock_profile.py` verifies the contract using fixture market, scan, and portfolio data.
- Investment Committee backend contract was added on July 25, 2026:
  - `GET /investment-committee` aggregates latest watchlist candidates, committee statuses, blockers, pending approvals, submitted orders, portfolio exposure, and active risk limits.
  - this is read-only and intended to support a future Claude Code Investment Committee view without touching broker execution.
  - `test_investment_committee.py` verifies ready, alert, pending approval, and portfolio exposure fields.
- Approval payload audit guard was added on July 25, 2026:
  - `/paper/execute/{queue_id}` now rejects malformed/stale payloads with `APPROVAL_AUDIT_FAILED`.
  - required payload fields include `preview.quote_snapshot`, PASS Shariah and risk agent summaries, approval status `APPROVED_PAPER_READY`, and empty preview blockers.
  - tests cover missing quote snapshots and stale blockers before any adapter call.
  - row-vs-payload consistency checks now reject mismatched preview, quote, and approval candidate symbol/side/quantity/price/notional fields.
- Mark-to-market portfolio valuation was added on July 25, 2026:
  - `GET /portfolio` now prices open positions through the existing Tiingo market-data path with `allow_fallback=false` and `allow_stale_cache=true`.
  - Dashboard Portfolio/Risk shows market value, unrealized P&L, and exposure weight.
  - Current AAPL valuation from local check: latest close `321.66`, source `tiingo_cache_after_error`, price date `2026-07-23`, market value `321.66`, unrealized P&L `-0.20`.
- Portfolio/exposure tracking was added on July 24, 2026:
  - `GET /portfolio` returns positions, fills, total cost basis, realized P&L, and valuation placeholders.
  - Queue id `54` was synced into the local portfolio ledger.
  - Position: `AAPL`, quantity `1.0`, average cost `321.86`, cost basis `321.86`, account MARGIN ending `1740`.
  - Portfolio sync audit event id: `355`.
- Paper order reconciliation succeeded on July 24, 2026:
  - Queue id: `54`
  - Broker order id: `3129776`
  - Reconciled status: `BROKER_FILLED`
  - Moomoo order status: `FILLED_ALL`
  - Dealt quantity: `1.0`
  - Dealt average price: `321.86`
  - Account: MARGIN ending `1740`
  - Audit event id: `354`
  - The queue payload now stores `broker_reconciliation` and `broker_reconciliation_history`.
- Controlled Moomoo paper execution succeeded again on July 24, 2026:
  - Queue id: `54`
  - Broker order id: `3129776`
  - Broker status: `BROKER_SUBMITTED`
  - Broker order status: `SUBMITTING`
  - Environment: `SIMULATE`
  - Account: MARGIN ending `1740`
  - Symbol/code: `AAPL` / `US.AAPL`
  - Quantity/price: `1` @ `333.74`
  - Audit event id: `353`
  - The queue payload contains the raw `broker_submission` adapter response.
- Dashboard now has a Paper Orders panel that should show this order after Refresh.
- Controlled Moomoo paper execution succeeded on July 22, 2026:
  - Dashboard produced an `APPROVED_PAPER_READY` AAPL queue item.
  - `Execute Paper` submitted to Moomoo paper/simulate.
  - Moomoo Papertrade notification reported the order was filled.
  - Queue label now shows `Broker Submitted` for broker-submitted rows.
- Adapter finding from the test:
  - Moomoo returned a US-compatible SIMULATE MARGIN account for `US.AAPL`.
  - Do not require SIMULATE account type to be `CASH`; require active `SIMULATE` and market-compatible account selection.
- Current useful scanner state: AAPL and PANW are alert candidates, not ready trades.
- AAPL example:
  - price: `326.59`
  - trigger: `333.74`
  - distance: `7.15`
  - status: `ALERT`
  - blocker: `quant_no_buy_signal`
- PANW example:
  - price: `348.66`
  - trigger: `358.68`
  - distance: `10.02`
  - status: `ALERT`
  - blocker: `quant_no_buy_signal`
- `ALERT` means monitor only. Approval should remain disabled until a row becomes `READY` with Quant `BUY` and Breakout OK.

## Reference Inspiration: FinceptTerminal

Source reviewed: https://github.com/Fincept-Corporation/FinceptTerminal

Important constraint:

- Treat FinceptTerminal as design and architecture inspiration only.
- Do not copy code, assets, agent prompts, screens, or proprietary structure into this project without a license review.
- The repository is dual-licensed AGPL-3.0 plus a Fincept commercial license, and its README/license text says commercial or internal company use requires a paid commercial license.

What is useful for Amanah Trader:

1. Terminal-style information architecture
   - FinceptTerminal organizes finance workflows as a full terminal: research, portfolio, news, analytics, trading, and workflow screens.
   - For Amanah Trader, adapt the concept as dashboard modules: Overview, Watchlist, Opportunities, Stock Profile, Approval Queue, Paper Orders, Portfolio/Risk, and Audit.

2. Python analytics boundary
   - Their docs describe Python analytics/data scripts returning JSON to the native app.
   - Our project already has this shape with FastAPI and Python modules. Keep extending small deterministic services with JSON contracts rather than building one large monolith.

3. Agent taxonomy
   - FinceptTerminal emphasizes many specialized agents: trader/investor, economic, geopolitics, and research agents.
   - For Amanah Trader, build fewer but higher-trust agents first: Shariah, Quant, Risk, Market Data, Portfolio Exposure, News/Event, and Investment Committee.

4. Data connector mindset
   - FinceptTerminal highlights many data connectors: market, macro, government, SEC/EDGAR, FRED/IMF/World Bank, and alternatives.
   - Prioritize connectors that improve our strategy decisions: SEC filings, earnings calendar, macro rates, sector/industry data, analyst fundamentals, and halal/compliance datasets.

5. Visual workflow idea
   - Their node-editor/workflow concept is interesting, but too large for the immediate path.
   - A lighter version for us: a readable decision pipeline view showing Shariah -> Market Data -> Quant -> Risk -> Approval -> Execution, with each node storing inputs, outputs, blockers, and timestamps.

Recommended future work inspired by this:

1. Rename queue status `Broker On` to `Broker Submitted`.
2. Add a dedicated Paper Orders page:
   - broker order id
   - submitted/fill status
   - account suffix
   - environment
   - execution timestamp
   - raw adapter response
3. Add a Stock Profile page:
   - Shariah result
   - Tiingo price/history
   - trend/breakout chart
   - latest scanner status
   - risk sizing preview
4. Add an Investment Committee view:
   - one row per candidate
   - agent votes and blockers
   - human decision notes
   - full audit trail
5. Add a connector roadmap:
   - SEC/EDGAR
   - FRED macro data
   - earnings calendar
   - fundamentals/ratios
   - halal universe enrichment
6. Consider a future local AI analyst only after deterministic data and audit flows are reliable.
