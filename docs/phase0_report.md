# Phase 0 — Data Validation Report

**Date:** 2026-07-07
**Tickers tested:** 30
**Passed quality checks:** 30
**Quarantined:** 0
**Quarantine rate:** 0.0%

**Exit criterion:** <2% quarantine rate on validation set.
**Result:** PASS

## Per-ticker results

| Ticker | Sector | Currency | Close (GBX) | Last date | Status | Flags |
|--------|--------|----------|-------------|-----------|--------|-------|
| SHEL.L | Energy | GBp | 2980.50 | 2026-07-07 | OK | — |
| AZN.L | Healthcare | GBp | 14394.00 | 2026-07-07 | OK | — |
| HSBA.L | Financials | GBp | 1462.90 | 2026-07-07 | OK | — |
| ULVR.L | Consumer | GBp | 4752.50 | 2026-07-07 | OK | — |
| GSK.L | Healthcare | GBp | 2023.00 | 2026-07-07 | OK | — |
| BARC.L | Financials | GBp | 520.40 | 2026-07-07 | OK | — |
| LLOY.L | Financials | GBp | 114.68 | 2026-07-07 | OK | — |
| RIO.L | Materials | GBp | 6893.00 | 2026-07-07 | OK | — |
| GLEN.L | Materials | GBp | 514.60 | 2026-07-07 | OK | — |
| BP.L | Energy | GBp | 473.00 | 2026-07-07 | OK | — |
| VOD.L | Telecom | GBp | 98.80 | 2026-07-07 | OK | — |
| REL.L | Industrials | GBp | 2473.12 | 2026-07-07 | OK | — |
| DGE.L | Consumer | GBp | 1582.29 | 2026-07-07 | OK | — |
| NG.L | Utilities | GBp | 1238.50 | 2026-07-07 | OK | — |
| LSEG.L | Financials | GBp | 9050.00 | 2026-07-07 | OK | — |
| AAL.L | Materials | GBp | 3663.86 | 2026-07-07 | OK | — |
| ANTO.L | Materials | GBp | 3805.95 | 2026-07-07 | OK | — |
| CHG.L | Healthcare | GBp | 565.00 | 2026-07-07 | OK | — |
| KNOS.L | Technology | GBp | 782.50 | 2026-07-07 | OK | — |
| JET2.L | Consumer | GBp | 1334.00 | 2026-07-07 | OK | — |
| CCH.L | Consumer | GBp | 5120.00 | 2026-07-07 | OK | — |
| WEIR.L | Industrials | GBp | 2492.00 | 2026-07-07 | OK | — |
| MONY.L | Financials | GBp | 194.80 | 2026-07-07 | OK | — |
| PETS.L | Consumer | GBp | 186.10 | 2026-07-07 | OK | — |
| MNDI.L | Materials | GBp | 715.40 | 2026-07-07 | OK | — |
| HIK.L | Healthcare | GBp | 1593.00 | 2026-07-07 | OK | — |
| PRU.L | Financials | GBp | 1037.74 | 2026-07-07 | OK | — |
| IMI.L | Industrials | GBp | 2864.00 | 2026-07-07 | OK | — |
| SMWH.L | Consumer | GBp | 417.80 | 2026-07-07 | OK | large_jumps_1 |
| OXIG.L | Industrials | GBp | 2936.00 | 2026-07-07 | OK | — |

## Notes

- Prices normalised to GBX (pence) internally.
- `repair=True` is NOT used on yfinance (can corrupt GBp data).
- Add FINNHUB_API_KEY to `.env` for cross-validation.
