# Amanah Trader Handoff

## Current State

Amanah Trader is currently a local-first, Shariah-aware paper trading control system with a multi-agent architecture.

Current mode:

- `TRADING_MODE=approval`
- `PAPER_EXECUTION_ENABLED=false`
- live trading disabled
- broker submission disabled

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
- Locked paper execution endpoint.

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
3. Run agents for `AAPL`.
4. Confirm:
   - Shariah Agent: PASS / US
   - Quant Agent: BUY or NO_SIGNAL
   - Risk Engine: PASS
   - Broker Submission: Disabled
5. If ready, approve the paper order.
6. Confirm it appears in Approval Queue.
7. Click Execute Paper.
8. Confirm result is `EXECUTION_LOCKED` while `PAPER_EXECUTION_ENABLED=false`.

## Useful Checks

```powershell
cd C:\Users\G2\OneDrive\Documents\Ai_Finance_Syariah\backend
..\.venv\Scripts\python.exe test_local_api_smoke.py
..\.venv\Scripts\python.exe check_market_data.py AAPL --strict
..\.venv\Scripts\python.exe check_zoya.py AAPL
..\.venv\Scripts\python.exe check_moomoo_status.py
```

Expected good signs:

- smoke test passes
- Tiingo source is `tiingo`
- Zoya status is `COMPLIANT` for AAPL
- Moomoo status is `paper_account_ready`

## Next Plan

Next recommended build step:

1. Add typed confirmation for paper execution:
   - require phrase: `EXECUTE PAPER`
   - backend rejects without the phrase
   - dashboard prompt/input before execution

2. Add real Moomoo paper execution adapter behind all gates:
   - `TRADING_MODE` must allow it
   - `PAPER_EXECUTION_ENABLED=true`
   - approval queue row must be `APPROVED_PAPER_READY`
   - Shariah PASS required
   - Risk PASS required
   - active SIMULATE CASH account required
   - broker submission recorded in queue and audit

3. After paper execution works, add market/investment-firm features:
   - watchlist
   - opportunities page
   - stock profile page
   - market overview
   - portfolio/exposure view
   - investment committee review page

Do not jump to autonomous paper mode until manual paper execution is reliable and fully audited.
