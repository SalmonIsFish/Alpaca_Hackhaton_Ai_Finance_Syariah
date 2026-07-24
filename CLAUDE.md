# Amanah Trader / AI Finance Syariah Handoff

## Current Purpose

This repo is a local-first Shariah-compliant paper-trading workflow. It uses deterministic agents for Shariah, quant, and risk checks before anything can enter the approval queue. Broker submission is paper-only and must stay behind explicit gates.

## Safety Rules

- Live trading is disabled by design. Keep `MOOMOO_MODE=paper`.
- Paper broker submission must remain opt-in through `/paper/execute/{queue_id}` with confirmation phrase `EXECUTE PAPER`.
- Do not bypass Shariah, quant, risk, approval, or confirmation gates.
- Do not commit or print secrets from `backend/.env`.
- Use local tests before changing broker-facing code.

## Run Commands

From repo root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn local_api:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open dashboard:

```text
C:\Users\G2\OneDrive\Documents\Ai_Finance_Syariah\dashboard\index.html
```

Focused tests:

```powershell
.\.venv\Scripts\python.exe backend/test_local_api_smoke.py
.\.venv\Scripts\python.exe backend/test_portfolio_risk_limits.py
python backend/test_portfolio_store.py
python backend/test_paper_execution_gates.py
python backend/test_moomoo_paper_adapter.py
```

## Current State

- Latest known filled paper order: queue `54`, broker order `3129776`, `AAPL BUY 1`, filled at `321.86`.
- Local portfolio has `1.0 AAPL`, account suffix `1740`, account type `MARGIN`.
- `/portfolio` marks positions to market using Tiingo/cache with no fixture fallback.
- `PAPER_ACCOUNT_EQUITY` defaults to `10000` and is used as the denominator for risk exposure percentages.
- Risk limits are configurable through env vars: `MAX_POSITION_PCT`, `MAX_TOTAL_EXPOSURE_PCT`, `MAX_LOSS_PER_TRADE_PCT`, `MAX_DAILY_LOSS_PCT`, and `MAX_ORDERS_PER_DAY`.
- Default position limit is `5%`; default total exposure limit is `25%`.
- BUY add-ons for an existing symbol are blocked by policy.
- SELL previews are reduce-only: they can become ready only when the local paper position exists and sell quantity does not exceed local quantity.
- Dashboard shows readable blocker messages in Agent Summary, Investment Committee, and Approval Queue.
- Dashboard has a Risk Policy panel showing account equity, risk limits, total exposure, add-on policy, and the current ticket state.
- Portfolio rows have a `Reduce` button that loads a SELL ticket from the local position.

## Good Next Tasks

1. Redesign the dashboard information architecture. The current single-page dashboard has too many stacked panels and requires too much scrolling. Claude Code should make this more user-friendly, likely with tabs or sections for Order Ticket, Portfolio/Risk, Paper Orders, Opportunities, and Audit/Diagnostics.
2. Add a dedicated Positions page or table with clearer partial-reduce controls.
3. Add a controlled SELL paper execution test after manually confirming Moomoo paper behavior.
