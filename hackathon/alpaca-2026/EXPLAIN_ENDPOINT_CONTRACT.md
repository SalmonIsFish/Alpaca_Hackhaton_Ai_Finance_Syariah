# `GET /stock/{symbol}/explain` — response contract

**SUPERSEDED.** Terminal 2 shipped the real endpoint (merged into `master`, shape pinned by
`backend/test_shariah_explain.py`) and it does not match the draft below: top-level keys are
`verdict` (an object: `status`/`tradeable`/`statement`, not a flat `overall_verdict` string),
`rule` (singular, with a `tests[]` array carrying `margin_pct` per test), `fiqh_basis` (an array
of `{principle, claim, citation}`), `evidence`, and `provenance` — there is no `steps` array and
no `overall_verdict` field. The "no frontend change needed" claim below was checked and found
false; the panel needs to be rewired to the real shape. Kept for history, not as documentation of
current behavior — see `backend/shariah_explain.py` for the real one.

---

Drafted by Terminal 1 (frontend) against the coordination doc's handoff contract in
`PARALLEL_WORK_SPLIT.md`, since Terminal 2 had not published a shape yet as of 2026-08-19.
This is what the Shariah Trace panel in `dashboard/index.html` consumes. If Terminal 2's real
implementation needs a different shape, change this file and the panel's `fetchExplainSteps` /
`renderTraceSteps` functions together — the field names below are exactly what the JS reads.

## Request

```
GET /stock/{symbol}/explain
GET /stock/{symbol}/explain?structure=covered_call
```

`structure` is optional (`covered_call` | `cash_secured_put`, lowercase — matches the dashboard's
`optionStrategy` select, lowercased) and only meaningful for an option ticket. Omit it for a
plain equity explain. `account_type` is deliberately **not** a query param — the endpoint should
resolve the live account context itself the same way `local_api.broker_account_context()` does,
rather than trusting a client-supplied value for a Riba gate.

## Response

```json
{
  "symbol": "AAPL",
  "overall_verdict": "PASS",
  "steps": [
    {
      "gate": "underlying",
      "label": "Underlying Shariah Screen",
      "verdict": "PASS",
      "rule_id": "sc_business_activity_sic",
      "rule_fired": "Business activity by SIC code, then debt/assets and cash/assets ratios each < 33%",
      "fiqh_basis": "SC Malaysia / SAC two-tier screening methodology",
      "citation": "docs/shariah-policy/screening-criteria-breakdown.md",
      "evidence": { "provider": "SEC_EDGAR", "debt_ratio": 0.275, "cash_ratio": 0.152, "report_date": "2025-09-27" }
    },
    {
      "gate": "option_structure",
      "label": "Option Structure Gate",
      "verdict": "PASS",
      "rule_id": "covered_by_owned_shares",
      "rule_fired": "Agent holds >= 100 shares of a Shariah-PASS underlying per contract",
      "fiqh_basis": "Ownership precedes the sale of a right, satisfying the possession requirement",
      "citation": "Usmani, Introduction to Islamic Finance -- Equity, stock ownership.md, via SHARIAH_GATE_NOTES.md",
      "evidence": { "structure": "covered_call", "shares_held": 100 }
    },
    {
      "gate": "account",
      "label": "Account Riba Gate",
      "verdict": "PASS",
      "rule_id": "cash_account_no_margin_exposure",
      "rule_fired": "Account type is CASH, no margin capability",
      "fiqh_basis": "No standing riba exposure from margin capability",
      "citation": "Riba.md, via SHARIAH_GATE_NOTES.md",
      "evidence": { "account_type": "CASH" }
    }
  ]
}
```

- `steps` is an ordered array; the dashboard renders whatever subset comes back (an equity-only
  explain naturally omits `option_structure` and can omit `account` too — the panel handles a
  1-element array fine).
- `verdict` is `"PASS"` | `"REJECT"` | anything else (rendered as an unstyled/neutral badge —
  the panel only special-cases `"PASS"` as ok-styled, everything else renders as the bad style,
  matching the gate chain's fail-closed default).
- `rule_id` is not currently read by the frontend but include it — it's the obvious future key
  for the trade-history view sketched (not built) alongside this panel, and for de-duplicating
  citations if a symbol is explained repeatedly.
- `fiqh_basis` and `citation` should map onto `shariah_trace.py`'s `STRUCTURE_RATIONALE` /
  `ACCOUNT_RATIONALE` dicts and the allow-list table in `SHARIAH_GATE_NOTES.md` — that table
  already has verdict, condition, and rationale+source per structure, so this is close to a
  direct port rather than new writing.

## Why the frontend isn't blocked on this

The dashboard's `renderApprovalGateBreakdown()` first renders a client-side parse of the existing
flat `shariah_trace` string (already returned by `POST /paper/approval`) into this same
`{gate, label, verdict, rule_fired, fiqh_basis, citation}` shape, using a citation lookup table
mirrored from `SHARIAH_GATE_NOTES.md`. It then calls this endpoint; on success the richer
server-provided steps (with `evidence`, and citations traceable to primary screening data rather
than a hardcoded client table) replace the fallback in place. On 404/network failure (endpoint
not built yet) the fallback stays. No frontend changes should be needed when this endpoint ships
— only a shape mismatch would require one, hence this doc.
