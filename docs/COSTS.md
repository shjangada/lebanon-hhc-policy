# Costs: what is sourced and what is not

Source pack: `data/raw/costs/cost_ranges.csv` (48 rows, each with its own source, date, url, page and status `verified` / `secondary` / `not_found`; README alongside). Ingest: `src/beqaa/ingest/costs.py` writes `data/processed/cost_ranges.csv` and `data/processed/interventions.csv`.

## Option costs now derived (USD, low to high)
| Option (unit) | Range | How | Status |
|---|---|---|---|
| CHWs via women's organisations (10 CHW-years) | 12,000 to 54,000 | 10 x 12 months x $100 volunteer incentive (4b) to $450 outreach worker (4c); NGO CHW $300 (4a) is the central value | secondary (job postings); excludes supervision, training, transport |
| Soil + water screening (catchment) | 740 to 2,650 | ASSUMED 10 soil + 10 nitrate + 10 water-Cr samples x lab prices (6d soil $33-210, 6a nitrate $25, 6b Cr $16-30) | unit prices verified; sample count is an assumption |
| Mobile maternal unit (unit-year) | 331,200 to 1,209,600 | PROXY: 1,200-1,800 consultations/month x 12 x $23-56 per consultation (1d, IRC Jordan, non-Lebanon) | proxy only: no published MMU operating cost exists (1a not_found) |

The mock range for the mobile unit was $90,000-160,000; the proxy is 4 to 8 times higher, so at $1M the mobile unit funds about 1 unit-year instead of 7 (the ranking of options on cost per pathway changes accordingly).

## Still no published unit cost (kept as labelled assumptions, `is_mock=True`)
Hub-spoke + e-referral, transport vouchers, washing-water truck, sunflower + biochar plot, Cr(VI) speciation (price not found), health-worker top-ups (5d), a harmonised CHW rate (4e), mobile-unit operating cost (1a), a total delivery tariff (3f), LHF management % (8d), INGO indirect rate (8f). Routes to get them are in each row's `notes`.

## Not yet used
Fund overhead rows (8a-8g: MPTF 1%, UN agencies 7-8%, CBPF partner up to 7%, World Bank trust funds 2-12%) feed the escrow-vs-direct comparison (separate change). Maternity rows (3a-3g) and PHC per-service cost (2a: $20.03; 2b: $164.67 per person-year) are available for the cascade and PHC options.

All LBP figures use 89,500 LBP/USD (assumption). UNHCR stopped covering hospital care on 1 Dec 2025: its patient-share figures describe a scheme that has ended.
