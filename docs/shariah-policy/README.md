# Shariah policy notes

These notes are the human-readable basis for the compliance decisions the agent makes.
They are read by `backend/wiki_context.py` to *explain* a gate decision — they can never
override one. The decision rule, from `backend/explain_compliance.py`, is:

> External `NON_COMPLIANT`, `ERROR`, or `NOT_CONFIGURED` results remain rejected;
> notes explain but cannot override.

## What is here

| File | Purpose |
|---|---|
| `Riba.md`, `Gharar.md`, `Maysir.md` | The three core prohibitions the screen enforces |
| `Equity-stock-ownership.md` | Why share ownership is permissible in the first place |
| `Related.md` | Cross-links between the principles |
| `screening-criteria-breakdown.md` | The quantitative thresholds the screen applies |
| `margin-account-policy.md` | Why the broker account is capped at 1x, and what that does and does not claim |
| `universe-dataset-README.md`, `source-reconciliation-2026-05.md` | Provenance of the universe dataset |

The screening universe itself lives at `data/shariah-universe/2026-05-29.json` — the
Securities Commission Malaysia Shariah Advisory Council list (`dataset_id:
sc-sac-my-2026-05-29`, 688 records, published 2026-05-29), packaged with a validation
block. It is public regulatory data.

## What is deliberately not here

The working research vault behind these notes contains third-party books and long
verbatim extracts from them. Those are **not** redistributable and are excluded from
this repository:

- raw book PDFs
- bulk markdown conversions of those books
- chapter-summary notes consisting mainly of copied passages

Only original synthesis and public regulatory data are published here. Where a note
relies on a specific scholarly source, cite it by author, title and section rather than
reproducing the passage.

## Configuration

`backend/config.py` defaults to these in-repo paths, so a fresh clone runs with no setup:

```
SHARIAH_WIKI_PATH      -> docs/shariah-policy/
SHARIAH_UNIVERSE_PATH  -> data/shariah-universe/2026-05-29.json
```

Both can be pointed at a larger private vault by setting the environment variables in
`backend/.env`.

## Scope limitation

The universe dataset is a **Malaysian** (SC SAC) list. It does not cover US equities, so
US symbols are screened through the external provider configured by `ZOYA_API_KEY` /
`ZOYA_ENVIRONMENT` instead. Verify that provider is returning real screening results —
a sandbox environment may return placeholder data.
