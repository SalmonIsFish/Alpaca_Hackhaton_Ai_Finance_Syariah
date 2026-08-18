---
title: Source Reconciliation - SC/SAC May 2026
status: unresolved
last_reviewed: 2026-07-16
---

# Source Reconciliation - SC/SAC May 2026

## Official source

- Authority: Securities Commission Malaysia (SC) / Shariah Advisory Council (SAC)
- Effective date: 29 May 2026
- Official download: [SC/SAC May 2026 PDF](https://www.sc.com.my/api/documentms/download.ashx?id=9f03c706-607f-4fbe-b4c7-91afc352ee49)
- Local evidence: `00-Raw-Books-PDF/Shariah-compliant-May 2026_final.pdf`

## Reconciliation result

| Check | Result |
| --- | ---: |
| Official Table 3 total (PDF page 20) | 886 Shariah-compliant securities |
| Unique ticker codes extractable from the published list (PDF pages 21-39) | 884 |
| Difference | 2 |

The same discrepancy appears after extracting the original PDF, so it is not caused only by the vault's Markdown conversion. SC's public list page currently supplies the PDF but no companion CSV/XLSX download.

## Control decision

The May 2026 universe remains `NO_ACTIVE_DATASET`. The Shariah gate must reject all proposed orders until the difference is resolved with an authoritative source.

## Resolution options

1. Obtain a complete machine-readable list directly from SC, Bursa Malaysia, or a licensed market-data provider, with provenance and effective date.
2. Obtain written clarification from SC identifying the two securities included in the 886 total but absent from the published list.
3. Wait for the next SC/SAC publication and repeat the reconciliation before activation.

Do not activate the 884-record extraction by silently changing the expected count. That would weaken the control designed to prevent trading from incomplete compliance data.
