# Design: Portfolio Value History + News Room

Status: approved for a future implementation session — not yet built.
Date: 2026-08-19

## Context

After the dashboard reorg (tabs, option ticket, Shariah Trace, Market Overview, Execution
Audit — see `feature/dashboard-redesign` history), the user's feedback was that the UI felt
flat: no portfolio value graph, no market news. They asked to keep the existing dark
control-panel theme unchanged and add real substance instead of restyling.

Two gaps turned out to be more than a UI reshuffle:

- **Portfolio history**: `portfolio_store.py` only ever tracked current positions
  (`paper_positions`) and individual fills (`paper_fills`) — there is no stored time series of
  total portfolio value anywhere. A "money graph" needs data that doesn't exist yet.
- **News**: nothing in this repo fetches news. No provider, no credentials, no module.

Research done before this design (both cited so a future session doesn't have to re-derive them):

- Alpaca has a first-party News API (Benzinga-sourced, real-time + historical) — see
  [Historical News Data](https://docs.alpaca.markets/us/docs/historical-news-data) and the
  [News articles reference](https://docs.alpaca.markets/us/reference/news-3). Since this repo
  is already an Alpaca shop (`alpaca_market_data.py`, `alpaca_paper_adapter.py`), this is a
  same-credentials, no-new-signup fit — confirmed with the user as the chosen source.
- General investment-dashboard UX guidance (via
  [Lollypop's investment dashboard UX guide](https://lollypop.design/blog/2026/may/investment-dashboard-ux-design-guide/)):
  line chart with 1D/1W/1M/1Y/ALL range selection, absolute value **and** percentage shown
  together, up/down arrow icons alongside color for gain/loss (never color alone), essential
  totals kept visible while scrolling. These inform the frontend section below but do not
  require any new backend beyond what's specified here.
- Confirmed via `grep` that no historical-value table exists (only `paper_fills`,
  `paper_positions`, `approval_queue`) and that options positions specifically are not tracked
  in the portfolio at all (pre-existing Known Limitation #2 in `CLAUDE.md`) — ruling out
  "reconstruct history from fills" as a trustworthy approach for anything involving options.

User decisions locked in for this design (do not re-litigate in the implementation session
unless something concrete has changed):

1. Build real historical snapshotting starting now, **plus** a current-allocation breakdown
   chart for immediate value while history accumulates (the "both" option).
2. News source is Alpaca's News API, filtered to watchlist ∪ current positions.
3. No theme change. Same dark palette, same accent color — this is additive content, not a
   redesign.

## Subsystem 1 — Portfolio value history

### Storage

New table, same style as the existing `paper_positions`/`paper_fills` (`portfolio_store.py`
`ensure_portfolio_tables`):

```sql
CREATE TABLE IF NOT EXISTS portfolio_value_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    account_equity REAL,
    market_value REAL,
    cost_basis REAL,
    unrealized_pnl REAL,
    realized_pnl REAL,
    position_count INTEGER
)
```

### Capture trigger

No cron/background process exists in this local-first app, and none should be added just for
this. Instead: every time `/portfolio` is computed (already happens on every dashboard refresh),
opportunistically record a snapshot, throttled to at most once per 15 minutes — reusing the
exact pattern `opportunity_scanner.py` already uses for scan throttling
(`DEFAULT_SCAN_THROTTLE_MINUTES` in `local_api.py`), not a new throttle mechanism.

```python
# portfolio_store.py
def record_portfolio_snapshot(connection, snapshot: dict, *, throttle_minutes: float = 15.0) -> dict | None:
    """Insert a snapshot unless one was already captured within throttle_minutes.
    Returns the inserted row, or None if throttled (matches the scan-throttle
    return-None-when-skipped convention already used elsewhere)."""
```

Call this from wherever `/portfolio`'s handler already computes `portfolio_snapshot(...)` in
`local_api.py` — pass the same numbers already being returned to the client, don't recompute.

### Read endpoint

```
GET /portfolio/history
```

Returns recent snapshots (reasonable cap, e.g. last 500 rows) as a plain list. No `range` query
param — the frontend windows into 1D/1W/1M/ALL client-side from the full list, keeping the
backend a dumb, easily-tested read. Revisit only if the table grows large enough that this
becomes wasteful (unlikely for a personal local tool).

## Subsystem 2 — News room

### Fetch function

Add to `alpaca_market_data.py` (not a new module — it already owns the `data.alpaca.markets`
integration and the `alpaca_data_request` seam CLAUDE.md's testing conventions already name):

```python
def fetch_news(symbols: list[str], *, limit: int = 20) -> dict:
    """GET https://data.alpaca.markets/v1beta1/news via alpaca_data_request.
    Same credentials as market data (alpaca_credentials()). Returns the raw
    Alpaca response shape: {"news": [...], "next_page_token": ...}."""
```

Request shape confirmed from the Alpaca docs: `symbols` (comma-separated), `limit` (1–50,
default 10), `sort=desc`, same `APCA-API-KEY-ID`/`APCA-API-SECRET-KEY` headers already used for
trading/market-data calls. Each article: `headline`, `summary`, `source`, `url`, `created_at`,
`symbols`, `images`.

### Read endpoint

```
GET /news?symbols=AAPL,MSFT&limit=20
```

If `symbols` omitted, default to the union of the saved watchlist and current portfolio
position symbols (both already available via existing functions — `get_watchlist_settings` and
`portfolio_snapshot`).

### Frontend integration

New **News** tab. Lazy-loaded only when the tab is opened (own fetch, own button/badge) —
**not** added to `refreshStatus()`'s `Promise.all`, which is already large; news doesn't need to
block or slow down every other panel's refresh, and there's no reason to spend API calls on news
nobody is currently looking at.

## Frontend — portfolio chart

- Hand-rolled inline SVG line chart. No charting library, no CDN script tag — the dashboard
  currently has zero external script dependencies, and pulling one in for a single line chart
  would work against the app's local-first, single-file philosophy. A plain SVG `<polyline>`
  driven by the snapshot list is enough at this data scale.
- 1D/1W/1M/ALL range buttons filter the already-fetched snapshot list client-side (no repeated
  fetches per range).
- Alongside it: a current-allocation bar breakdown (per position, by exposure %) computed from
  the existing `/portfolio` response — useful on day one, before snapshot history exists.
- Gain/loss display: keep existing `ok`/`bad` color classes, but add a leading ▲/▼ (or similar)
  so the signal doesn't rely on color alone, per the UX research above. Small, additive — not a
  retheme.
- Placement: new panel(s) in the existing **Portfolio/Risk** tab, above or beside the current
  position list. Do not touch Committee, Stock Profile, Orders, Ticket, Market Overview, or
  Execution Audit — none of this design changes them.

## Testing plan (for the implementation session)

- TDD `record_portfolio_snapshot`'s throttle behavior (records when stale, skips within the
  window, returns `None` when skipped) — mirror `opportunity_scanner.py`'s existing throttle
  test style.
- TDD `fetch_news` with the network seam mocked (same convention as every other Alpaca call in
  this repo) — assert the request built (symbols, limit, headers), not just a canned response.
- Full backend regression suite must still pass (currently 30 suites green on
  `feature/dashboard-redesign`).
- Live-Chrome verification pass once built, same as the last dashboard round: confirm the SVG
  chart actually renders with real snapshot data (may need to manually trigger a few `/portfolio`
  calls first to accumulate more than one snapshot), confirm the News tab renders real Alpaca
  headlines, confirm nothing else regressed visually.

## Explicitly out of scope for this design

- No theme/palette changes.
- No options-position history (that's Known Limitation #2, a separate pre-existing gap this
  design doesn't attempt to close).
- No `range` query param on `/portfolio/history` — client-side windowing only, for now.
- No push/websocket news streaming — polling on tab-open only.
