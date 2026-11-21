# Cost ranges for Bekaa Valley health policy model

Compiled 2026-11-21. Data file: `cost_ranges.csv` (48 rows, one row per source or derived estimate).

## Columns
item_id, item, unit, low, central, high, currency, price_year, usd_low, usd_central, usd_high, geography, source_title, publisher, date, url, page_or_table, status, notes

- **status**: `verified` means the figure was read from the cited source. `secondary` means a news report, job posting, fundraising page, or a value we derived from verified figures (the notes say which). `not_found` means no citable figure; the notes give the best route to get one.
- Rows from outside Lebanon say **NON-LEBANON** in the `geography` column.
- **LBP to USD**: UNHCR 2025 PHC fees use 89,500 LBP/USD (the BDL official rate since 2024; our assumption). HAUS 2022 values use the survey's own average rate of 30,000 LBP/USD.
- EUR (IMDEA, 2024) and INT$ PPP (MSF Jordan) figures have not been converted. The usd_* columns are blank for those rows.

## Status by item
| # | Item | Status | Best anchor |
|---|------|--------|-------------|
| 1 | Mobile medical unit | Operating cost per month **not_found**. Proxies only | IRC Jordan cost per consultation $23-56 (2023 USD). Lebanon MMU throughput 1,200-1,800 consultations/month. IMANA $250k for 3 units (a fundraising target) |
| 2 | PHC consultation / LPSP | Found | K2P/UNICEF memo: $20.03 per service; $164.67 per capita per year (2022); LPSP visit fee $2 GP / $3.5 specialist; PHCC operating cost $200k-364k per year |
| 3 | ANC / NVD / C-section | Partly found | ANC paid out of pocket $13 (2022); IRC ANC full cost $35-41. Patient share under UNHCR: NVD $128-170, C-section $255-300. MoPH 2024 C-section tariff $1,060 (news report). Total NVD tariff **not_found** |
| 4 | CHW / outreach stipend | Found (job postings) | $100 (volunteer), $300 (CHW), $400-450 (outreach worker, Bekaa). Wage benchmarks: minimum wage $298, SMEB $403, cash-for-work $15/day. Harmonised sector rate **not_found** |
| 5 | Health worker top-ups | Benchmarks only. Donor top-up rates **not_found** | PHC salaries $200-1,000/month (2023); public civil-servant average $551/month (2024, IMF) |
| 6 | Soil / water testing | Water found (AUB 2025); soil total Cr derived; Cr(VI) **not_found** | Nitrate $25; Cr $30; soil total Cr about $130 (digestion $100 + metal $30, derived); US labs $33-210 |
| 7 | Solar for a PHC | Found | $1,175/kWp PV only (2018 PHC); $1,447/kWp with battery storage (UNDP 2026 award); 25 kWp PHC system $29k-63k (derived) |
| 8 | Pooled-fund overhead | Mostly found | MPTF agent fee 1%; UN indirect cost 7% (UNDP 8%); CBPF partner PSC up to 7%; World Bank trust funds 5%-2% recipient-executed / 12% bank-executed. LHF fund-management cost % and INGO 7-13% **not_found** |
| 9 | Chronic medication per patient | Partly found (derived proxies) | About $19 per beneficiary (WHO 2023, all medicines); $47.75 per capita (LPSP medicines share); MSF Jordan INT$1,424-1,904 per patient per year (whole programme). YMCA/EDP per-patient cost **not_found** |

## Caveats
- None of these numbers were invented. Derived values are flagged in the notes with their arithmetic.
- The UNHCR Annual Referral Health Care Report 2023 PDF could not be read here. It may contain the average cost per delivery.
- UNHCR stopped covering hospital care, including deliveries, on 1 Dec 2025, so the UNHCR patient-share figures describe a scheme that has ended. They still describe the cost burden.
