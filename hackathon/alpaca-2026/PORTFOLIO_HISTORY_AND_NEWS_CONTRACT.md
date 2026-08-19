# Portfolio history + news — handoff contract

Terminal 1 built everything that doesn't require touching `local_api.py` (off-limits per
`CLAUDE.md`). This is what's left for Terminal 2, and the exact shapes the dashboard already
consumes. Design spec: `docs/superpowers/specs/2026-08-19-portfolio-history-and-news-design.md`
(already approved — this doc doesn't relitigate any decision in it, just hands off the routes).

## What's already built and tested

- `backend/portfolio_store.py`: `portfolio_value_snapshots` table (in `ensure_portfolio_tables`),
  `record_portfolio_snapshot(connection, snapshot, *, throttle_minutes=15.0)`,
  `list_portfolio_snapshots(connection, *, limit=500)`. Tests: `test_portfolio_snapshot_history.py`
  (throttle records-when-stale / skips-within-window / returns-`None`-when-skipped, mutation-checked).
- `backend/alpaca_market_data.py`: `fetch_news(symbols, *, limit=20)` — single request (not the
  exhaustive pager), returns Alpaca's raw `{"news": [...], "next_page_token": ...}` shape, fails
  closed (`AlpacaDataError`) with no credentials or on a request error. Tests: `test_alpaca_news.py`
  (request shape, limit clamping 1–50, missing-credentials/request-failure raise), mutation-checked.
- `dashboard/index.html`: current-allocation breakdown (from the existing `/portfolio` response —
  no new backend needed for this part, already live), the SVG portfolio-value line chart with
  1D/1W/1M/ALL range buttons, and a lazy-loaded News tab. All three degrade gracefully (empty
  state, not an error) against the two endpoints below until they exist — same fallback pattern
  as the Shariah Trace panel's `/explain` handoff.

## What Terminal 2 needs to add to `local_api.py`

### 1. Call the snapshot recorder from the existing `/portfolio` handler

```python
@app.get("/portfolio")
def portfolio() -> dict:
    connection = db()
    try:
        snapshot = portfolio_snapshot_with_exposure(connection)
        record_portfolio_snapshot(connection, snapshot)  # <- add this line
        return snapshot
    finally:
        connection.close()
```

`record_portfolio_snapshot` already throttles itself (returns `None` and does nothing when called
within 15 minutes of the last snapshot) and reads the exact field names `portfolio_snapshot_with_exposure`
already returns (`paper_account_equity`, `market_value`, `total_cost_basis`, `unrealized_pnl`,
`total_realized_pnl`, `position_count`) — no reshaping needed, pass the dict straight through.

### 2. `GET /portfolio/history`

```python
@app.get("/portfolio/history")
def portfolio_history() -> dict:
    connection = db()
    try:
        return {"snapshots": list_portfolio_snapshots(connection)}
    finally:
        connection.close()
```

Response:
```json
{
  "snapshots": [
    {
      "captured_at": "2026-08-19T10:00:00+00:00",
      "account_equity": 25000.0,
      "market_value": 1200.5,
      "cost_basis": 1000.0,
      "unrealized_pnl": 200.5,
      "realized_pnl": 50.0,
      "position_count": 2
    }
  ]
}
```
Oldest first, capped at 500 rows. No `range` query param by design — the dashboard windows into
1D/1W/1M/ALL client-side from the full list.

### 3. `GET /news?symbols=AAPL,MSFT&limit=20`

```python
@app.get("/news")
def news(symbols: str | None = None, limit: int = 20) -> dict:
    connection = db()
    try:
        if symbols:
            selected = [s.strip() for s in symbols.split(",") if s.strip()]
        else:
            # Union of the saved watchlist and current portfolio positions, per the design doc.
            watchlist = get_watchlist_settings(connection)["symbols"]
            positions = [p["symbol"] for p in portfolio_snapshot_with_exposure(connection)["positions"]]
            selected = sorted(set(watchlist) | set(positions))
    finally:
        connection.close()
    return fetch_news(selected, limit=limit)
```

Response is `fetch_news`'s raw pass-through: `{"news": [{"headline", "summary", "source", "url",
"created_at", "symbols", "images", ...}], "next_page_token": ...}` — the dashboard reads exactly
those field names, not a reshaped version.

## Why the frontend isn't blocked

Same pattern as `EXPLAIN_ENDPOINT_CONTRACT.md`: the dashboard's portfolio-history chart and News
tab both try their endpoint and render an empty/"not yet available" state on 404 rather than
erroring, so nothing needs to change on the frontend once these two routes and the one
`record_portfolio_snapshot` call land — only a shape mismatch would require a frontend change,
and the shapes above are exactly what's already implemented and tested on the store/adapter side.
