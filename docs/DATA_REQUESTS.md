# Data requests and manual steps (drafts, nothing has been sent)

Every request below replaces a mock or assumed input. Contact addresses appear only where a source in the repo gives one (`lebhealthsector@who.int`, `ceelabs@aub.edu.lb`); for the others find the official contact first (do not guess an address). Fill in your name and affiliation; keep the request narrow, ask for aggregates, say what you will cite, and offer to share the result.

| # | Replaces | Ask | Route |
|---|---|---|---|
| 1 | `water_quality` (mock) | Well / river nitrate and other results, Beqaa, 2024-2026, with site coordinates or village | Litani River Authority; also the Ministry of Environment |
| 2 | `staffing_referrals` (mock); facility status (4 dated) | Names and status of PHCCs closed or functioning in Bekaa and Baalbek-Hermel in 2026; posts filled vs budgeted; referrals sent / completed | Lebanon Health Sector (`lebhealthsector@who.int`); MoPH PHC department |
| 3 | `soil_sites` coordinates, Cr(VI) | Coordinates for the BE sample IDs and the ID-to-value link (Table 2.3); any Cr(VI) speciation | CNRS-L / Ministry of Environment (report authors); AUB lab (`ceelabs@aub.edu.lb`) for a Cr(VI) speciation price and turnaround |
| 4 | `governance_capacity` (mock) | District or municipal series behind the UN-Habitat rapid assessment | UN-Habitat Lebanon (RMA team) |
| 5 | `vulnerability` within-district | VASyR 2025 / MSNA 2025 district-level aggregates or microdata | UNHCR / WFP / UNICEF (VASyR), REACH / IMPACT (MSNA) |

## Draft 1: Litani River Authority / Ministry of Environment
Subject: Request for Beqaa water-quality monitoring data (nitrate), 2024-2026

We are a student team (2026 MIT Policy Hackathon, Born Global Foundation / Impossible Lebanon challenge) analysing how soil and water findings should trigger health protection in the Beqaa Valley. We are looking for any monitoring results for wells or the Litani River in Zahle, West Bekaa, Rachaya, Baalbek and Hermel since 2024: nitrate (mg/L) and any other measured parameters, with sampling date and site name or coordinates. Aggregates by village or sub-basin are fine. We will cite the Authority as the source, mark anything we cannot verify as an assumption, and are happy to share our results. Could you tell us whether this is available, in what format, and whom to ask?

## Draft 2: Health Sector (lebhealthsector@who.int)
Subject: Request: functioning status of PHCCs and staffing/referral data, Bekaa and Baalbek-Hermel, 2026

We are analysing primary-care access in the five Beqaa districts and found only national counts of closed PHCCs (e.g. 43 to 59 between March and May 2026) with no names. Could you share, or point us to, (a) the list of network PHCCs and hospitals in Bekaa and Baalbek-Hermel with their functioning status and date in 2026 (aggregate by caza is acceptable if names cannot be shared); (b) posts budgeted vs filled and referrals sent / completed per facility or caza, if collected; (c) the Inter-Agency PHC masterlist of 25 March 2025 and any 4W/5W health partner mapping by governorate. We will cite the source and label what we cannot verify.

## Draft 3: CNRS-L / Ministry of Environment (soil), cc AUB lab
Subject: Request: sample coordinates and Cr(VI) speciation for the April 2026 post-war soil report (Beqaa samples)

We use Table 2.3 of the CNRS-L / MoE post-war recovery soil report (Beqaa BE sample IDs). The report gives no coordinates and no link from sample ID to value, so we can only place five villages at village level. Could you share the coordinates (village level is enough) for the BE samples and the ID-to-value table, and say whether hexavalent chromium (Cr(VI)) speciation was measured? To AUB lab (`ceelabs@aub.edu.lb`): what is the price and turnaround for Cr(VI) speciation in soil (e.g. EPA 3060A/7196A)? Your 2025 price list gives total Cr only.

## Draft 4: UN-Habitat (RMA)
Subject: Request: municipal / district series from the Rapid Municipal Assessment

We model administrative capacity of municipalities in the Beqaa. The published RMA gives national aggregates only. Is a district-level or municipality-level table available (capacity or service indicators), even anonymised or banded?

## Draft 5: UNHCR / REACH (VASyR, MSNA)
Subject: Request: district-level VASyR 2025 / MSNA 2025 tables, Beqaa

We analyse access to care for displaced Syrians and host communities in the five Beqaa districts. The published findings are national or governorate level. Could you share district-level tables (access barriers, insurance, female-headed households), or the process for a microdata request?

## ACLED (local use only; data cannot be committed or deployed)
1. Sign in at <https://acleddata.com> and open your account page. Check that API access is enabled for your tier; if not, use their access request form.
2. Put `ACLED_EMAIL=` and `ACLED_PASSWORD=` in `.env` (quotes optional; gitignored).
3. `python -m beqaa.ingest acled`. On HTTP 403 the script stops and does not retry.
4. Keep the ACLED attribution on any figure that uses it. Do not commit `data/raw/conflict_events/acled/` or `conflict_events*.csv`.

## Verify by hand (extracted from PDFs)
- `data/raw/facilities/moph_bekaa/moph_facilities_bekaa.csv`: PHC names, villages, phones vs the MoPH network PDF (`moph.gov.lb/userfiles/files/HealthCareSystem/PHC/phcc.pdf`; 404 on 2026-11-21, ask MoPH for the current copy). About 3 newer network centres are missing.
- `data/raw/beqaa_funding/beqaa_health_partners.csv`: the 39 PHCC operators against the MoPH PHCC list of 16/04/2026 (`phcc-16-4-2026.pdf`, pp. 18-22); the pack warns the extraction may have missed rows (the Annual Dashboard counts 37 + 28).
- `women_led` for every organisation in `org_registry.csv`: check on each organisation's own site; leave `to_verify` until then.
- `data/raw/damage_roads/damage/published_figures_transcribed.csv` (when ingested): automated extraction, check against the PDFs.

## Items still open after the 2026-11-21 research pass (what could and could not be found)
| # | Item | Result | What is needed |
|---|---|---|---|
| 1 | Host projects and funder add-on rules | ILO table-grape call: Activity 4.1 is awareness-raising only; call expired 23 Aug 2026, no award shown. Fair Trade Lebanon: RFQ page found (633 participants, Baabda and Baalbek), says "Self-Funded", PPE already bought. Nabad: nothing found. CBPF reprogramming and GATE safeguards documents all returned 403 | open the CBPF Data Hub pages for CBPF-LEB-25-S-NGO-38001 and CBPF-LEB-26-R-NGO-40017; download the CBPF Global Guidelines (revision rules) and the CDR ESCP / LMP / ESMF for GATE; ask the LHF Humanitarian Financing Unit whether a testing and referral activity can be added by budget revision |
| 2-3 | CHW case-management and pesticide-protection evidence | see `docs/EVIDENCE_TABLE.md` (agent results merged where verified) | |
| 4 | Prices | AUB lab list read (nitrate $25, total chromium $30, E. coli $40, total coliforms $25, chlorine $35, lead $30). NOT found: Cr(VI) price (AUB has total Cr only), regional PPE kit price, freight into Lebanon, field water-test kit prices | email ceelabs@aub.edu.lb for a Cr(VI) and soil-metals quote; request quotes from Lebanese suppliers for PPE kits |
| 5 | Newer settlement locations | none public: only national totals (221,283 people received sanitation help in informal settlements and collective shelters, Q4 2025) | request the current IAMP site list from UNHCR Lebanon information management or the WASH sector |
| 6 | Baalbek centre visit volumes | Amel total 224,180 consultations in 2025 (no geographic split); MoPH Annual Dashboard 2025 PDF could not be opened | open the dashboard PDF from a machine that can reach intouchmena.com; ask the operators for per-centre volumes |
