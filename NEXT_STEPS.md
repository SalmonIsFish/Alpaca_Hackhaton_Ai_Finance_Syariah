# Amanah Trader Handoff

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
