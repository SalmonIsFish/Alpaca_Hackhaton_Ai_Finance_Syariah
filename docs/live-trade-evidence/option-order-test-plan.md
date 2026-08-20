# Live Level 1 option order — test run plan and stop criteria

**Status:** prepared 2026-08-20, gate chain proven, broker submission not yet attempted.
**Account:** `0TCX` — the **test** paper account, not the hackathon account.
**Mode:** this is a deliberately small, throwaway test order whose purpose is to prove the
option path reaches `filled`. It is a debugging proxy for the competition-account run on
2026-08-28, not the demo trade itself.

## Why this run exists

`NEXT_STEPS.md` §4: no *option* order has ever run end to end live. Both Level 1 structures
are exercised only against a mocked `alpaca_request` seam in `test_option_execution_smoke.py`,
and that suite sends `test_fixture: true`, which injects **both** a Shariah override and a
quant override. So the live unknowns are option symbology (OCC-21), strike/liquidity selection
against a real chain, and whether the `alpaca_mcp` transport's `place_option_order` behaves as
its schema claims. Those are exactly the things a mock cannot tell you.

## What is already proven, before any broker contact

Run on 2026-08-20 while the market was closed, against real SEC data and a real option chain:

| step | result |
|---|---|
| contract selection | `CVX260821P00197500` — 4.0% OTM, 1 DTE, bid 0.13 / ask 0.14, spread 7.4% of mid |
| `POST /paper/preview` | `READY_FOR_APPROVAL` — shariah PASS, quant BUY, risk PASS |
| `POST /paper/approval` | `APPROVED_PAPER_READY`, queue 6 |
| trace | underlying=PASS (SEC_EDGAR) · structure=cash_secured_put PASS (100% cash-collateralized purchase commitment, Arboun/Wa'd; no margin financing) · account=CASH PASS |

Everything up to the broker is therefore proven. What remains unproven is the submission
itself, which needs the market open and a human typing `EXECUTE PAPER`.

## Why CVX and not SPY or AAPL

Both of the originally preferred underlyings are unavailable, and for *different* reasons —
worth recording, because one of them is the gate working and the other is not.

- **SPY** — rejected by the Shariah gate: `sec_company_facts_unavailable:http_404`. An ETF has
  no company facts on EDGAR, so the screen fails closed. Correct behaviour; SPY is off the
  table on principle, not on liquidity.
- **AAPL** — blocked by the **quant agent**, not by any Shariah gate: `quant_no_buy_signal`,
  price 6.71% below the 339.71 breakout level. Its Shariah screen passes on real SEC data.
- **CVX** — Shariah PASS (debt 13.3%, cash 2.2%) *and* quant BUY. Of 21 liquid large caps
  scanned, only CVX and LLY carried a BUY signal; LLY at ~$1,280 needs more collateral than
  the account holds.

## Order to place

Sell to open **1** contract (not the 5 the collateral would support — deliberately small):

```powershell
.venv\Scripts\python.exe backend\check_paper_order.py CVX --option cash_secured_put --contracts 1
.venv\Scripts\python.exe backend\approve_paper_order.py CVX
.venv\Scripts\python.exe backend\execute_paper_order.py <queue_id>   # asks for the phrase
```

Re-run the preview **fresh at market open**; the staged one above is priced off the prior
close and will be stale. Queue 6 should be left unexecuted for that reason.

The limit defaults to the contract's **bid**, which makes a sell-to-open marketable so it
crosses rather than resting in the spread. The point of this run is a `filled` status, not a
successful submission — an `accepted` order that never fills proves nothing.

## Success criteria

All four, or the run has not succeeded:

1. `POST /paper/execute/{queue_id}` returns a broker order id.
2. The order reaches Alpaca status **`filled`** — not `accepted`, `new`, or `pending_new`.
3. Reconcile returns `OPTION_FILL_RECORDED` and writes to `paper_fills` under the OCC symbol.
4. `paper_positions` is **untouched**. Options are not tracked as positions by design
   (`CLAUDE.md` known limitation 2); booking contracts as shares was a real bug once and must
   not reappear.

## Stop / pause criteria

Stop the run and escalate rather than working around any of these:

| observation | why it stops the run |
|---|---|
| **Any gate rejects** | That is the gate working. Record the rejection as evidence and stop. Do not relax a gate, re-pick a symbol to dodge a Shariah verdict, or widen the strike band to find something that passes. |
| **The OCC symbol is malformed or Alpaca rejects the contract** | Symbology bug in `build_option_occ_symbol`. Fix under test, do not hand-edit a symbol to get one order through. |
| **`place_option_order` rejects a well-formed body** | Transport/schema mismatch in the MCP surface. Pull current docs before changing the body; do not guess at field names. |
| **The order fills at a price the ledger does not agree with** | This is the failure mode the CVX equity trade nearly hit — `sync_filled_order` computes `float(dealt_avg_price or price)`, and `0.0` is falsy, so a null fill price silently books the *limit*. Stop and verify three ways: local ledger, broker position, order `filled_avg_price`. |
| **An option fill lands in `paper_positions`** | Known-limitation 2 has regressed. Stop immediately; this corrupts equity exposure math at 1/100th true size. |
| **The account stops reporting `CASH`** | `account_shariah_gate` will reject everything. Re-check `provision_cash_account.py`; do not proceed on a margin account. |
| **Assignment risk becomes material** | A 4% OTM 1-DTE put should expire worthless. If the underlying moves toward the strike, assignment means buying 100 CVX for $19,750 — permitted and cash-secured, but it changes account state before the competition run. Decide deliberately, do not discover it. |

## Systemic flaw surfaced and fixed — 2026-08-20

`agent_coordinator.evaluate_candidate` requires `quant.signal == "BUY"` for **every** order,
including sell-to-open options. This is not a Shariah gate; it is an equity momentum signal.

Consequences:

- A **covered call** is gated behind a breakout signal on stock you already own, which is
  close to backwards — covered calls are typically written when momentum has stalled.
- On any given day most compliant names will be blocked. On 2026-08-20, 19 of 21 liquid large
  caps carried no BUY signal. **If 2026-08-28 looks like today, the competition run could find
  no eligible underlying at all.**
- `test_option_execution_smoke.py` cannot catch this: `test_fixture: true` injects
  `quant_override` with `signal: "BUY"`, so the option path has never run against a real quant
  signal until now.

This is the same class as the two equity-only rules already fixed in that file — the BUY-only
side restriction and the equity risk overlay applied to contracts/premium.

**Resolved the same day**, on the project owner's decision, after being reported rather than
adjusted unilaterally. The filter is now scoped to non-option orders:

```python
if asset_class != "option" and quant.get("signal") != "BUY":
    blockers.append("quant_no_buy_signal")
```

which mirrors the side restriction one line above it. No gate was touched — the quant agent is
a strategy filter, not one of the six protected gates. Ownership and collateral are still proven
by `option_structure_gate` and `account_shariah_gate` at approval time, and the signal is still
reported in `agent_summary.quant`, just not as a blocker.

Verified on live data, same symbol at the same moment:

| order | before | after |
|---|---|---|
| AAPL cash-secured put, 1 contract, sell to open | `REJECT` — `quant_no_buy_signal` | `READY_FOR_APPROVAL`, quant reported as `NO_SIGNAL` |
| AAPL equity BUY @ 316.90 | `REJECT` — `quant_no_buy_signal` | `REJECT` — `quant_no_buy_signal` (unchanged, correctly) |

Mutation-checked three ways — reverting the fix, dropping the filter for equity too, and
inverting which asset class is exempt — each caught by both `test_agent_coordinator.py` and
`test_option_execution_smoke.py` scenario 5.
