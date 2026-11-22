# Health riders on already-funded projects: shortlist and verification (2026-11-21)

A rider = testing (soil or water), a trigger to screening and referral at the nearest MoPH-list primary-care centre, and protection for everyone working the land. Costs come from sourced unit prices (`data/processed/cost_ranges.csv` items 6a, 6b, 6c, 4a-4c, 2a) times sample counts that are **assumptions** (`src/beqaa/riders.py`, shown as parameters). Source: the project inventory (`data/raw/projects`, desk search) and `data/registry/projects_verification.csv`.

**Finding to confirm, not a proven fact:** none of the 37 inventoried projects tests soil contamination or screens people for exposure. Pages were read through a summarising tool and several returned 403, so the absence is the result of a desk search.

**Host projects are optional.** No host project could be confirmed, so the rider is funded through the proposed LHF Beqaa window (registry F004); a host project's own safeguard or OHS line only lowers the new money needed.

## What could and could not be verified
Only the ILO notice, the BALADNA pages (EEAS, AFD) and the SPNL page could be opened. The HDX/CBPF pages (Nabad, Fair Trade Lebanon) and the UNDP pages (Hermel, GATE grants) were blocked, so those rows rest on search summaries. **Do not cite an amount, date or implementer from this table without opening the source page yourself.**

| Project | Verified | Discrepancy with the inventory |
|---|---|---|
| P25 Nabad: emergency and sustainable water supply, Baalbek / Zahle (LHF CBPF-LEB-25-S-NGO-38001, USD 450,000) | no | nothing could be checked; whether it is still active is unknown (approved 29 Dec 2025, no end date in the export) |
| P03 UNDP / KfW agricultural support, Hermel (with the Union of Hermel Municipalities) | partly | no amount or dates stated; "coordination" wording unconfirmed; no soil, water or health component (only pest-management training) |
| P01 Climate-Smart Matching Grants (GATE, USD 20M) | partly | CDR is the grant provider, MoA and the General Directorate of Cooperatives lead, UNDP supports; "World Bank as funder" and "grantees being selected" not confirmed; no Bekaa share stated |
| P08 ILO table grapes, Bekaa | partly | the page is a call for proposals marked Expired (deadline 23 Aug 2026), no award shown: "active" is unsupported; funder not stated; Activity 4.1 is awareness-raising on occupational safety and health, not screening |
| P05 BALADNA (EUR 32.15M: EU 24.8M, Denmark about 5.35M, AFD 2M) | yes (funders, amounts) | end date conflicts (EEAS 2026-2029, AFD to 1 Jun 2030); no implementer named; soil, water, health are not named components |
| P22 Fair Trade Lebanon cash-for-work (LHF CBPF-LEB-26-R-NGO-40017) | no | governorates differ from the shortlist ("Baalbek only") |
| P13 SPNL Upper Litani (DIMFE, Jun 2025 to Nov 2026, 14 villages) | partly | only the Litani River Authority confirmed as partner; lab training is for industrial wastewater, not household wells |

## Rider cost per project (`processed/riders.csv`, 12 projects at district or cadaster precision)
Central $3,800 to $4,200 per rider (range about $2,600 to $4,800), which is 0.5% to 0.9% of the budget where a USD budget is known. These are not quotes: sample counts (40 nitrate and 40 chromium tests per water project, 6 CHW months, 100 screenings at $20.03) are assumptions. Projects at governorate or national level (P01, P05, P08) have no rider row until the implementer gives site lists; the earlier shortlist cost estimates for them ($6,500 to about $10,250) used illustrative counts.

## Hooks that fit
- **Water and irrigation projects** (water_testing): test sources for nitrate (AUB 2025, $25) and chromium ($30) before handover; above-limit results trigger household drinking-water advice and referral.
- **P37, a solar well in Chmestar** (cadaster 53429): the one project found in a village with a CNRS-L soil finding (chromium). The nearest centre in the MoPH list is in Chmestar itself (about 3 minutes). Whether the well is tested for chromium is not stated.
- **Cash-for-work and livelihoods** (worker_protection): PPE and a health check at enrolment (PPE has no sourced price).
- **water_hygiene** (new hook): drinking-water nitrate priced; microbial tests, household water-treatment guidance and menstrual and postpartum hygiene supplies have no sourced price and are listed as unpriced.

## Collateral-damage check for riders
- Money pegged to landowners may miss Syrian workers: require services for all workers regardless of legal status.
- Test results can stigmatise land or crops (market harm): results go to households and the clinic first, not to buyers.
- A rider can overload one centre (flagged when it adds more than 10% of a centre's assumed yearly capacity).
- Funders may refuse scope creep: use the project's own safeguard or OHS lines where allowed, otherwise a ring-fenced Beqaa window.
