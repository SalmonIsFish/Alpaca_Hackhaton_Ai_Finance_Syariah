# Amanah Trader / AI Finance Syariah Handoff

## Current Purpose

This repo is a local-first Shariah-compliant paper-trading workflow. It uses deterministic agents for Shariah, quant, and risk checks before anything can enter the approval queue. Broker submission is paper-only and must stay behind explicit gates.

Latest shutdown checkpoint: `89b6e1b Add investment committee API contract` on July 25, 2026 02:03 +08:00. Git working tree was clean before this handoff update.

## Safety Rules

- Live trading is disabled by design. Keep `MOOMOO_MODE=paper`.
- Paper broker submission must remain opt-in through `/paper/execute/{queue_id}` with confirmation phrase `EXECUTE PAPER`.
- Do not bypass Shariah, quant, risk, approval, or confirmation gates.
- Do not commit or print secrets from `backend/.env`.
- Use local tests before changing broker-facing code.

## Claude Code Skills To Consider

Use these only after reviewing the installed `SKILL.md` files and confirming the current security audit status on https://www.skills.sh/audits. Prefer skills with Gen Agent Trust Hub, Socket, and Snyk pass results. Do not install skills with pending, failed, high-risk, or unclear audit status unless the user explicitly approves after review.

Recommended for the next UI/dashboard pass:

```powershell
npx skills add https://github.com/anthropics/skills --skill frontend-design
npx skills add https://github.com/anthropics/skills --skill webapp-testing
npx skills add https://github.com/obra/superpowers --skill verification-before-completion
npx skills add https://github.com/mattpocock/skills --skill git-guardrails-claude-code
```

Optional token/context management skills:

```powershell
npx skills add https://github.com/affaan-m/everything-claude-code --skill strategic-compact
npx skills add https://github.com/muratcankoylan/agent-skills-for-context-engineering --skill context-compression
```

Why these:

- `frontend-design`: use for redesigning `dashboard/index.html` into a more usable trading control dashboard.
- `webapp-testing`: use to verify the local FastAPI dashboard flow with browser/UI checks after redesign.
- `verification-before-completion`: require fresh test or browser evidence before claiming the UI/backend task is done.
- `git-guardrails-claude-code`: add Claude Code hooks that block dangerous git commands such as hard reset, clean, forced push, and broad restore/checkout.
- `strategic-compact`: optional; use to trigger `/compact` at phase boundaries such as research -> plan -> implementation -> test, instead of waiting for automatic compaction.
- `context-compression`: optional; use only for long sessions or handoff summaries where preserving key decisions matters more than minimizing a single message.

Token budget guidance for Claude Code:

1. Do not install every useful-looking skill. Each skill can add discovery and instruction overhead.
2. For the next session, install only `frontend-design`, `webapp-testing`, `verification-before-completion`, and `git-guardrails-claude-code`. Add `strategic-compact` only if the session gets long.
3. Before editing, read `CLAUDE.md`, `NEXT_STEPS.md`, `dashboard/index.html`, and only the backend endpoints needed for `/investment-committee`, `/stock/{symbol}/profile`, and `/portfolio`.
4. Avoid dumping full files into chat unless needed. Use targeted search, line ranges, diffs, and summaries.
5. Use `/compact` after finishing a major phase, especially before switching from UI design to test/debug work.
6. Keep handoff notes short and factual: changed files, commands run, results, remaining risks, and next action.

Skill installation safety checklist:

1. Install from the exact GitHub repository and skill name above, not a similarly named package.
2. Check the skill page on `skills.sh` for audit status immediately before installing.
3. After install, inspect added `SKILL.md` files and any scripts/hooks before running them.
4. Keep the install project-local when possible.
5. Do not install browser automation, cloud, trading, broker, wallet, or secret-management skills for this repo unless there is a specific task and a separate security review.

## LangGraph / LangChain Guidance

Do not integrate LangGraph or LangChain in the immediate UI pass. The current core agents are deterministic Python functions, which is the right shape for Shariah, quant, risk, approval, and broker safety gates.

Use this rule:

- Keep Shariah PASS/REJECT, quant signal rules, risk limits, approval audit checks, SELL reduce-only checks, and broker execution gates as plain tested Python.
- Consider LangGraph later when the workflow needs durable orchestration across Shariah -> market data -> quant -> portfolio risk -> investment committee -> human approval -> paper execution -> reconciliation.
- Consider LangChain later only for read-only LLM research agents, such as news/event summaries, SEC filing summaries, earnings transcript analysis, halal evidence explanations, and natural language portfolio Q&A.
- Do not allow any LangChain or LLM agent to directly approve, bypass, or submit broker orders.

Possible future architecture:

```text
Deterministic core:
Shariah -> Market Data -> Quant -> Risk -> Approval Candidate

LangGraph orchestration:
Workflow state, retries, human-in-the-loop approval, audit timeline, reconciliation state

LangChain / LLM research:
Read-only summaries and explanations, never execution authority
```

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
.\.venv\Scripts\python.exe backend/test_investment_committee.py
.\.venv\Scripts\python.exe backend/test_stock_profile.py
.\.venv\Scripts\python.exe backend/test_market_overview.py
.\.venv\Scripts\python.exe backend/test_positions_api.py
.\.venv\Scripts\python.exe backend/test_portfolio_store.py
.\.venv\Scripts\python.exe backend/test_paper_execution_gates.py
.\.venv\Scripts\python.exe backend/test_moomoo_paper_adapter.py
.\.venv\Scripts\python.exe backend/test_risk_checks.py
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
- Portfolio ledger tests cover partial and full SELL fills, including realized P&L after a position is closed.
- Moomoo adapter tests cover SELL side mapping without contacting OpenD.
- `/paper/preview` stores a read-only `quote_snapshot` for audit, and approval queue payloads preserve it.
- `/paper/execute/{queue_id}` has an execution-time reduce-only SELL guard against the local paper portfolio and active account suffix.
- `/paper/execute/{queue_id}` also audits the stored approval payload and rejects missing quote snapshots, non-PASS agent summaries, stale blockers, or non-approved payload status before adapter submission.
- Execution audit cross-checks approval queue row fields against the stored preview, quote snapshot, and approval candidate before broker submission.
- Portfolio fill sync rejects filled SELL reconciliations that exceed the local position, so bad or stale broker reconciliation cannot silently distort local holdings.
- `/stock/{symbol}/profile` provides a read-only backend contract for Shariah status, market data, latest opportunity scan result, local portfolio exposure, and active risk limits.
- `/investment-committee` provides a read-only aggregate of latest watchlist candidates, committee statuses, pending approvals, submitted orders, portfolio exposure, and risk limits.
- `/market-overview` provides a read-only watchlist health contract with latest saved scan coverage, ready/alert/data-error counts, data freshness/source counts, stale cache symbols, recent alert events, and portfolio exposure.
- `/positions` provides a read-only flattened positions contract with valuation, exposure status, and max reduce quantity for future position-management views or agents.

## Good Next Tasks

1. Redesign the dashboard information architecture. The current single-page dashboard has too many stacked panels and requires too much scrolling. Claude Code should make this more user-friendly, likely with tabs or sections for Order Ticket, Portfolio/Risk, Paper Orders, Opportunities, Stock Profile, Investment Committee, and Audit/Diagnostics.
2. Use `GET /investment-committee` as the backend contract for the Investment Committee view instead of re-aggregating data in the browser.
3. Use `GET /market-overview` as the backend contract for a future market health or watchlist overview page.
4. Use `GET /stock/{symbol}/profile` as the backend contract for a future stock detail page.
5. Use `GET /positions` for a future dedicated Positions page or table with clearer partial-reduce controls.
6. Add a controlled SELL paper execution test after manually confirming Moomoo paper behavior.
