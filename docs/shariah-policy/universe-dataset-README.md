---
title: Shariah Universe Data Layer
status: active-design
last_reviewed: 2026-07-16
---

# Shariah Universe Data Layer

This folder is the machine-readable source of truth for the Malaysian equity eligibility gate. The raw SC/SAC document remains the evidence; generated records are a controlled derivative of it.

## Folder layout

```text
shariah-universe/
├── universe-manifest.json       # points to the only dataset eligible for use
├── schema.json                  # validation contract for a universe dataset
├── versions/                    # immutable, date-stamped validated datasets
└── staging/                     # incomplete or unverified imports; never tradeable
```

## Activation rule

Only a dataset whose `validation.status` is `validated` and whose identifier equals `active_dataset_id` in `universe-manifest.json` may pass the Shariah gate. A missing, stale, incomplete, or unverified dataset means `REJECT`.

## Import process

1. Download or retain the official SC/SAC list and store its source URL and publication date.
2. Run `tools/import-shariah-universe.ps1` with the expected official count.
3. The importer writes to `staging/` when the count does not reconcile. It never activates an incomplete import.
4. Review ticker/name mismatches and the source metadata.
5. Move a fully reconciled version to `versions/`, set `validation.status` to `validated`, and update the manifest in the same reviewed change.
6. Preserve all prior versions. Refresh after the SC's May and November list updates.

## Current status

The May 2026 Markdown snapshot advertises 886 compliant securities but presently produces only 688 unique ticker records after parsing and de-duplication. It is intentionally not active until a complete official source or a reconciled dataset is provided.

## Related notes

- [[06-Agent-Design-Specs/shariah-gating-rules]]
- [[06-Agent-Design-Specs/audit-log-spec]]
