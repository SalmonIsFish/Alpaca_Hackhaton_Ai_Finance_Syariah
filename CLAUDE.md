# Amanah Trader — Claude Code Working Notes

## What this is

A local-first, Shariah-compliant paper-trading control system. Deterministic Python agents
screen every order for Shariah compliance, option-structure permissibility, account-level Riba
exposure, and risk limits **before** it can enter the approval queue, and a human must type a
confirmation phrase before anything reaches the broker.

The point is not the screening — plenty of products screen stocks. The point is that the gate
chain **enforces** and **proves**: an order that fails any gate cannot be submitted, and every
decision is recorded with its evidence.

Broker: **Alpaca**, paper only.

## Safety rules (these override convenience)

- **Live trading must remain impossible.** `ALPACA_MODE` is pinned to `paper` in
  `config.load_settings()`, and `alpaca_paper_adapter.ALPACA_PAPER_BASE_URL` is a hardcoded
  paper host with no live URL anywhere in the module and no env var that can repoint it. The
  MCP transport forces `ALPACA_PAPER_TRADE=true` on the server it spawns.
- Broker submission stays opt-in behind `POST /paper/execute/{queue_id}` with the confirmation
  phrase `EXECUTE PAPER`.
- Do not bypass or weaken the Shariah, option-structure, account, risk, approval, or
  confirmation gates. If a gate is inconvenient, that is the gate working.
- Broker adapters perform **no** compliance checks of their own. They submit what an
  already-gated approval says to submit. Compliance lives in the gate chain, not the adapter.
- Never commit or print secrets from `backend/.env`. `.env` has never been committed — keep it
  that way. `backend/.env.example` documents the variables with empty values.
- Run the local tests before changing anything broker-facing.

## Architecture

```
Preview          POST /paper/preview
                   market data -> quant signal -> risk limits -> quote snapshot
                   carries asset_class + option_contract for option orders

Approval         POST /paper/approval
                   local_api.broker_account_context()  resolves live broker facts:
                     shares_held      <- portfolio_store.open_position_quantity
                     cash_collateral  <- settled cash (NEVER buying_power)
                     account_type     <- Alpaca multiplier (CASH / MARGIN)
                     uses_margin      <- conservative: account_type == MARGIN
                   shariah_candidate.build_shariah_candidate(...)  <-- the ONE gate entry point
                   approval_workflow.approve_candidate(...)
                     -> shariah_gate          is the company permissible?
                     -> option_structure_gate is the contract permissible?
                     -> account_shariah_gate  is the account free of Riba?
                   APPROVED_PAPER_READY | REJECT(reason)

Execution        POST /paper/execute/{queue_id}   requires "EXECUTE PAPER"
                   paper_execution.py re-audits the stored payload, re-checks reduce-only SELL
                   -> alpaca_paper_adapter.submit_paper_order(approval, broker)

Reconcile        POST /paper/reconcile/{queue_id}
                   -> portfolio_store.sync_filled_order  (equity only; see Known limitations)
```

### Module ownership

| Concern | Files |
|---|---|
| Broker + market data | `alpaca_paper_adapter.py`, `alpaca_market_data.py` |
| Gate chain | `shariah_gate.py`, `option_structure_gate.py`, `account_shariah_gate.py`, `shariah_candidate.py`, `agents/` |
| Compliance data | `sec_edgar_screen.py` (self-built SC screen), `zoya_compliance.py` (sandbox only) |
| Strategy | `option_strategy.py` — proposes a contract; approves nothing |
| Orchestration | `local_api.py`, `paper_execution.py`, `approval_workflow.py`, `agent_coordinator.py` |
| State | `approval_queue.py`, `portfolio_store.py`, `watchlist_store.py` |
| Legacy | `moomoo_*.py` — superseded by Alpaca, retained for history. Do not extend. |

**`shariah_candidate.build_shariah_candidate()` is the only surface a broker adapter talks to.**
Adapters never import a gate module directly. If something a gate needs isn't reaching it, fix
the plumbing on the adapter side rather than changing the gate contract.

## Configuration

Everything is read via `os.getenv` in `config.load_settings()` from `backend/.env`.
See `backend/.env.example` for the full list. The ones that change behaviour most:

| Variable | Default | Notes |
|---|---|---|
| `ALPACA_API_KEY_ID` / `ALPACA_SECRET_KEY` | — | Paper keys. User sets these; never ask for them in chat. |
| `ALPACA_MODE` | `paper` | Any other value raises at startup. |
| `PAPER_EXECUTION_ADAPTER` | `disabled` | `disabled` \| `fake` \| `alpaca` \| `alpaca_mcp` \| `moomoo` |
| `PAPER_EXECUTION_ENABLED` | `false` | Master lock on broker submission. |
| `MARKET_DATA_PROVIDER` | `alpaca` | `alpaca` \| `tiingo` |
| `ZOYA_ENVIRONMENT` | `sandbox` | **Sandbox returns randomized data.** See Known limitations. |
| `TRADING_MODE` | `approval` | `advisory` \| `approval` \| `autonomous_paper` |
| Risk limits | see example | `MAX_POSITION_PCT`, `MAX_TOTAL_EXPOSURE_PCT`, `MAX_LOSS_PER_TRADE_PCT`, `MAX_DAILY_LOSS_PCT`, `MAX_ORDERS_PER_DAY` |

`SHARIAH_UNIVERSE_PATH` and `SHARIAH_WIKI_PATH` default to committed in-repo copies
(`data/shariah-universe/`, `docs/shariah-policy/`), so a fresh clone runs with no `.env` at all.
Set them only to point at a larger private vault.

## Alpaca integration

Two transports, both paper-only, selected by `PAPER_EXECUTION_ADAPTER`:

- **`alpaca`** — REST over stdlib `urllib` against `https://paper-api.alpaca.markets`.
- **`alpaca_mcp`** — the official MCP server via `uvx alpaca-mcp-server` (needs `uv`; override
  the command with `ALPACA_MCP_COMMAND`). The server wraps every payload in a
  `{"_alpaca_mcp_security": {...}, "data": {...}}` trust envelope; `unwrap_mcp_envelope()`
  strips it. That envelope is a prompt-injection guard aimed at LLM callers — this adapter reads
  named fields out of `data` deterministically and never treats tool output as instructions.

Options are **Level 1 only**: sell covered call, sell cash-secured put, and closing those shorts.
Multi-leg spreads are rejected by design. Contracts are built as OCC-21 symbols with
`time_in_force=day` and an explicit `position_intent`.

Market data (`alpaca_market_data.py`) mirrors `tiingo_prices.fetch_eod_prices` exactly — same
signature, same bar shape — so `market_data.summarize_history` switches providers with nothing
downstream noticing. It also exposes `fetch_option_contracts` / `fetch_option_snapshots` /
`fetch_option_chain` for strike selection. On a plan that cannot query recent SIP data it
automatically retries on the IEX feed and labels the source `alpaca_iex`.

## Running it

From the repo root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn local_api:app --app-dir backend --host 127.0.0.1 --port 8000
```

or `backend\run_local.ps1`. Dashboard: open `dashboard\index.html`.

Config check (prints booleans, never values):

```powershell
.\.venv\Scripts\python.exe backend\check_config.py
```

## Tests

Every test is a plain script with a `main()` that prints `PASS: ...`. No pytest. Run them
individually:

```powershell
.\.venv\Scripts\python.exe backend\test_alpaca_paper_adapter.py
.\.venv\Scripts\python.exe backend\test_alpaca_market_data.py
.\.venv\Scripts\python.exe backend\test_alpaca_execution_wiring.py
.\.venv\Scripts\python.exe backend\test_alpaca_shariah_wiring.py
.\.venv\Scripts\python.exe backend\test_option_execution_smoke.py
.\.venv\Scripts\python.exe backend\test_sec_edgar_screen.py
.\.venv\Scripts\python.exe backend\test_option_strategy.py
.\.venv\Scripts\python.exe backend\test_shariah_candidate.py
.\.venv\Scripts\python.exe backend\test_option_structure_gate.py
.\.venv\Scripts\python.exe backend\test_account_shariah_gate.py
.\.venv\Scripts\python.exe backend\test_option_fill_ledger.py
.\.venv\Scripts\python.exe backend\test_repo_defaults.py
.\.venv\Scripts\python.exe backend\test_paper_execution_gates.py
.\.venv\Scripts\python.exe backend\test_execution_audit.py
.\.venv\Scripts\python.exe backend\test_portfolio_store.py
.\.venv\Scripts\python.exe backend\test_risk_checks.py
.\.venv\Scripts\python.exe backend\test_local_api_smoke.py
.\.venv\Scripts\python.exe backend\test_moomoo_status.py
```

32 suites pass. `check_moomoo_status()` pre-checks TCP reachability before touching the moomoo
SDK, so a closed OpenD port fails in ~1.5s instead of the SDK's own multi-minute retry/backoff —
this is what used to make `test_local_api_smoke.py` and the dashboard's status refresh hang;
both now complete fast with no Moomoo gateway running. `test_moomoo.py` still hangs by design:
it instantiates the moomoo SDK directly, bypassing that pre-check, since its purpose is to
manually verify a *real* OpenD connection when you actually have one running — it is the one
suite not run as part of the regular list above.

### Testing conventions

- Network access goes through one replaceable module-level seam — `alpaca_request`,
  `alpaca_data_request`, `load_alpaca_mcp_client`, `check_alpaca_status`. Tests swap the seam;
  they never hit a real API.
- Prefer asserting the *request that was built*, not just the response that came back.
- When a test passes on the first run, break the code deliberately and confirm the test fails.
  Several real bugs in this repo were found exactly that way.

## Known limitations — read before claiming anything works

1. **US screening is live on SEC EDGAR, and every call is uncached.** `agents/shariah_agent.py`
   routes the US path to `sec_edgar_screen.check_us_symbol`, reporting `provider: SEC_EDGAR`.
   Zoya is no longer in the US path; `zoya_compliance.py` remains only for reference, and
   `us_strategy.py` still imports it directly (a second screening path — see NEXT_STEPS.md).
   Read the module docstring before trusting a verdict: business activity is approximated by
   SIC code, and XBRL cannot separate Islamic from conventional instruments, so both ratios
   are overstated. Both approximations err toward rejection.

   **Cost:** a screen is a live SEC fetch of up to ~4.7 MB and takes roughly 0.7–2 s, with no
   cache and no rate throttle. `/paper/preview` and `/stock/{symbol}/profile` now carry that
   on every call. The screening store in NEXT_STEPS.md is what fixes it. Tests are unaffected
   — they supply a `shariah_override` or swap the `sec_request` seam, and none reach SEC.
2. **Option fills are audited but not tracked as positions.** `portfolio_store` models whole
   shares only — no contract multiplier, strike, expiry, or assignment. `sync_filled_order`
   diverts option fills to `paper_fills` under the OCC symbol and returns
   `OPTION_FILL_RECORDED` without touching `paper_positions`. Alpaca is the source of truth for
   options P&L. Do not "fix" this by booking contracts as shares — that was a real bug.
3. **The strategy layer selects but is not wired to an endpoint.** `option_strategy.py` calls
   `fetch_option_chain` and picks a contract for both Level 1 strategies: 1–7 DTE, the strike
   closest to 4% OTM inside a 2–7% band, filtered for a live bid, a spread under 15% of mid, a
   minimum premium, and a standard 100-share multiplier; sized from owned shares or settled
   cash. It emits an `option_contract` that drops straight into `build_shariah_candidate`, and
   a `rationale` string narrating the choice. What is missing: no endpoint calls it, so a
   caller must supply `option_contract` to `/paper/preview` by hand or use
   `check_option_strategy.py`. Selecting is not approving — a selected contract still has to
   clear the whole gate chain, and `test_option_strategy.py` asserts exactly that.
4. **The end-to-end chain has never run against real Alpaca.** `test_option_execution_smoke.py`
   now exercises preview → approval → execute for a covered call, an unsupported strategy, a
   margin account, and an under-collateralized cash-secured put — through the real FastAPI app,
   with only the `alpaca_request` network seam mocked. That test is what found and fixed two real
   bugs: `agent_coordinator.evaluate_candidate` unconditionally blocked any non-BUY side, which
   made both Level 1 strategies (both are sell-to-open) unreachable from `/paper/preview` at all
   (fixed with an `asset_class` param); and the portfolio risk overlay treated an option's
   contracts/premium as if they were equity shares/share-price, producing nonsensical exposure
   percentages that would reject almost any option order once a real position existed (fixed by
   skipping that equity-specific overlay for `asset_class == "option"` — the option_structure_gate
   and account_shariah_gate already provide correct option-native sizing). What's still open:
   nobody has run this against the *real* Alpaca paper API with real credentials — only against a
   mocked network seam.

## Style

- Deterministic Python for anything that gates, screens, or executes. No LLM in the decision
  path — a language model may explain a decision but must never make, approve, or bypass one.
- Match the surrounding code: small pure functions, dict returns with a `status` key, fail
  closed on anything unknown.
- Keep `local_api.py` diffs small; it is the file most likely to be touched concurrently.
