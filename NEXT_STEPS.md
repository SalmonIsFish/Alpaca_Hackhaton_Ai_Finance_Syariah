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

First next build task:

1. Rename queue label `Broker On` to `Broker Submitted`.
2. Add a clearer Paper Orders section with broker order id, submitted/fill status, environment, account suffix, execution timestamp, and raw adapter response.
3. Keep FinceptTerminal as reference inspiration only; do not copy code/assets because of licensing constraints.

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
  - active SIMULATE CASH account required
  - broker submission recorded in queue and audit when adapter submits
- Real Moomoo adapter is available with `PAPER_EXECUTION_ADAPTER=moomoo`, currently limited to US equity paper orders such as `AAPL` -> `US.AAPL`.

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

1. Add watchlist persistence and alert history:
   - persist watchlist symbols and alert threshold in SQLite
   - remember the latest opportunity scan results
   - record alert events when symbols move between `NOT_READY`, `NEAR_BREAKOUT`, `ALERT`, and `READY`
   - add `GET /watchlist`, `POST /watchlist`, and `GET /opportunity-alerts`
   - dashboard should load saved watchlist settings on refresh
   - dashboard should show recent alert history

2. After watchlist persistence is reliable, run one controlled real Moomoo paper execution test:
   - keep Moomoo OpenD open and verify `paper_account_ready`
   - set `PAPER_EXECUTION_ENABLED=true`
   - set `PAPER_EXECUTION_ADAPTER=moomoo`
   - use a very small US paper order candidate
   - submit only through the dashboard `/paper/execute/{queue_id}` gate path
   - confirm returned order id/status is recorded in queue and audit

3. After paper execution works, add market/investment-firm features:
   - watchlist
   - opportunities page
   - stock profile page
   - market overview
   - portfolio/exposure view
   - investment committee review page

Do not jump to autonomous paper mode until manual paper execution is reliable and fully audited.

## Latest Operator Notes

- Controlled Moomoo paper execution succeeded on July 22, 2026:
  - Dashboard produced an `APPROVED_PAPER_READY` AAPL queue item.
  - `Execute Paper` submitted to Moomoo paper/simulate.
  - Moomoo Papertrade notification reported the order was filled.
  - Queue label currently shows `Broker On`; rename this to `Submitted` or `Broker Submitted` for clarity.
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
