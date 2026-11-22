# Beqaa Health Prioritization Framework & Dashboard

2026 MIT Policy Hackathon (Born Global Foundation / Impossible Lebanon). 

**Theme:** an adaptive funding switch for Beqaa primary care. Money follows measured need, and administrative control shifts from foreign NGOs to Lebanese entities (national NGOs, Unions of Municipalities, with MoPH co-governing) as measured capacity improves. Horizon 2030.

> **Status (2026-11-21):** no dataset is entirely mock. Real or sourced inputs drive the ranking; anything without a published value is a labelled slider, placeholder or proxy (see `docs/HEADLINE_AUDIT.md` and `docs/ASSUMPTIONS_PILOT.md`). The red MOCK watermark appears only if a dataset is entirely mock; sections that rest on assumed inputs say ASSUMED INPUTS. Mock files in `data/mock/` exist only for the tests.

## Run
```
python3 -m venv .venv && source .venv/bin/activate && pip install -e . pytest
make mock     # generate MOCK data in data/mock/ (tests only)
make ingest   # convert raw downloads to real datasets in data/processed/ (python -m beqaa.ingest all)
make all      # mock + full pipeline -> data/processed/ (models, break-evens, riders, unit costs, KPIs)
make test     # mock + pytest (150 tests)
make appendix # ingest + pipeline + 13 memo figures (figures/) + generated docs + notebook
make app      # Streamlit dashboard at http://localhost:8501
```
The Makefile uses `.venv/bin/python` (override with `make PY=python3 ...`).

## What the project does today (analyses and the data they use)

| Analysis (module) | What it answers | Data it uses | Status |
|---|---|---|---|
| **M1 Access** (`m1_access.py`): E2SFCA, pre-2026 vs 2026 closures, d0 sensitivity, mobile-unit siting (MCLP) | Q1: whose access is most constrained? | population, facilities, travel_time, cadasters | Runs on mock |
| **Group access** (`equity.py` + M1): access by host / displaced Lebanese / registered displaced Syrians / unregistered workers (est.) / women 15–49, gap vs host; optional demand weighting by group (WorldPop age/sex share × displacement counts × multiplier) | Q1, Q5: equity gaps | population (+ displacement columns) | Runs on mock; mock groups are near-uniform, so gaps are small until real data |
| **Facility resilience** (`m1_access.facility_risk`, `access_if_exposed_pause`): power source and conflict exposure of open facilities; access if exposed facilities pause | Q1, Q5 (resilience) | facilities (`power_source`, mock), conflict_exposure (mock stand-in for the LRP admin-3 incident table, real) | Runs on mock |
| **P1 Access panel** (`m1_access.access_panel`, dashboard section 2): per cadaster, before the war vs now: E2SFCA access, facilities per 10k, travel time to nearest PHC and hospital, share beyond 30 min (PHC) / 60 min (hospital); map and ranked chart share one metric; facility status is dated (functional / partial / closed / damaged / unknown shown grey), mobile units are part-time facilities (hours per week / 40); validation vs official health severity (Spearman ρ and disagreements); exposure × access target list; every layer date-stamped | Q1: whose access is most constrained | facilities (status_date), travel_time, population, official_severity, soil_sites, conflict_exposure | Runs on mock; status dates are mock; OSM facilities are all 'unknown' until a dated source (HeRAMS / Health Sector) is loaded |
| **Robustness** (`robustness.py`, `data/params/uncertainty.yaml`): Monte Carlo over uncertain parameters (catchment, weights, aggregation, Cr(VI) share) inside six stress scenarios (escalation, funding shock, power collapse, staff loss, capacity stall, worst-case contamination); the **core set** of cadasters that stay top-k everywhere; allocation-policy **regret** (prefer smallest maximum regret); **breakpoints** where 'community beats top-down' flips; escrow graceful-degradation check | all questions: does the recommendation survive if assumptions are wrong | all models; fixed seed; N = 1,000 draws per scenario | Runs on mock; scenario effects, costs and community priorities are assumptions |
| **M2 Need Score** (`m2_need_score.py`): 4 domains, 5,000 Dirichlet weight draws → `p_top_tier` and rank intervals; comparison with JIAF/FSA district severity; map layers (need, environment) | Q1, Q5: where to prioritise | M1 output, M4 tiers, vulnerability, water_quality, official_severity | Runs on mock; weights, thresholds and safe/crisis values are **assumptions** |
| **M4 Exposure screen** (`m4_exposure.py`): HQ ranges (Cr speciation unknown), Pb vs EPA screening level, Monte Carlo, tornado (what evidence would change the response), tiers 0–3 with a/b/c evidence rungs | Q2, Q4 | soil_sites, crop_transfer, exposure_params.yaml | Soil **values are real** (CNRS-L/MoE 2026), **locations mock**; reference doses need confirming in EPA IRIS |
| **M5 Options & budget** (`m5_options.py`): $1k / $100k / $1M tiers, fundable-or-not, Monte Carlo extra completed pathways, cost per pathway, equity-gap change, collateral-damage checklist | Q3 | interventions, cascade_baseline | Runs on mock; costs and lifts are **mock** |
| **Community allocation** (`allocation.py`): top-down vs per-capita vs community-decided with capture safeguards | Q3 (team theme) | M2 scores, M5 effects, mock community priorities | Effect of local choice is an **assumption** (range 1.0–1.3), not an estimate |
| **Escrow & funding switch** (`escrow.py`): need floor + capacity tranche, editable thresholds, administrator ladder INGO → national NGO → Union of Municipalities (MoPH co-governs, not assumed to administer by 2030; renewed-escalation scenario), lock-out and gaming warnings, restricted vs unrestricted | Q3, Q5 | M2 scores, governance_capacity and staffing_referrals (mock **scenario inputs**: no public source, the pilot would measure them) | Runs on mock; thresholds are assumptions |
| **Start-site scorer, rank stability** (`start_site.py`): where the pilot is cheapest to start (soil result, host project, centre access, settlements 2016, outreach, reported disease, need) with 1,000-draw weight stability and startup cost | Q3, Q4 | processed data above | Saadnayel (Zahle) first; no single cadaster is stable, choose a district and a cluster |
| **Pilot flow** (`pilot_flow.py`): referral funnel, visit and test schedule, WHO sampling floor, capacity-aware routing, break-even CHW share | Q2, Q5 | sliders (no Beqaa data); 72% settlement water positivity (WaSH Sector) | assumptions are sliders |
| **M6 illness averted** (`m6_illness_averted.py`): reported hepatitis A + typhoid averted and cost per NOTIFIED case (upper bound) | Q4 | MoPH ESU 2023-25, Wolf 2022 RR (transferred), sourced prices | $7,900-22,800 per notified case |
| **Riders, unit costs, KPIs** (`riders.py`, `unit_costs.py`): testing + referral add-on per project, unit-cost table, KPIs mapped to escrow triggers with equity splits | Q3, Q5 | AUB, UNICEF, K2P prices; escrow rules | counts are assumptions |
| **Break-evens and sensitivity** (`breakeven.py`, `sensitivity.py`): when community beats status quo; one-way tornado of the pilot numbers | Q4 | scenario parameters | no published values |
| **Funding finder + registry chat** (`funding_finder.py`, `chat.py`): rank registry rows, recency and "fits escrow?" flags; grounded retrieval that refuses when nothing matches | Q3 | `data/registry/*.csv` (22 funding rows, 53 organisations; most org rows are `to_verify`) | Registry rows from team research 2026-11-21; re-check before use |

Dashboard: one scrolling page with eight sections (Why Beqaa · Care and disease today · Funding today · Priority areas · Control of the money · Pilot design · Resilience · Funding sources) and a jump-link bar, plus a separate Methods page (the detailed model views). Interventions carry a feasibility filter (F1–F8) from `docs/FEASIBILITY.md`. Every mock file is listed in `data/registry/mock_provenance.csv` with the real source it stands in for and how obtainable it is (a test enforces this).

Not built yet: M3 network simulation (a light version is `pilot_flow.py`), a Workforce page, OSM-road travel times, escrow overhead in the escrow-vs-direct comparison, a Beqaa-specific measured funding share (only a title-keyword proxy exists).

## Running the app
```
make app           # localhost:8501 from this folder (shows whichever branch is checked out here)
make app-stable    # localhost:8502 from a separate worktree that tracks origin/main (scripts/run_stable.sh)
```
`.streamlit/config.toml` sets `runOnSave = true`: the app reruns by itself when a `.py` file in `app/` or `src/beqaa` changes. New CSVs in `data/processed/` or `data/registry/` are picked up on the next rerun (press **R** in the browser): the app's cache is keyed to file timestamps. If `requirements.txt` changes, stop the server, `pip install -r requirements.txt`, restart. The stable worktree (`../lebanon-hhc-main`, detached at `origin/main`) only changes when main changes; re-run `make app-stable` after each merge to update it.

## Data status: what is real and what is fake so far
**Short version:** the places, population, MoPH facility list, conflict incidents, food insecurity, official severity, funding flows, disease surveillance, soil (5 villages) and crop transfer factors are real or sourced. Water quality and staffing were removed (water exposure is unknown for every cadaster; referral completion and posts filled are sliders); governance uses national anchors for every district; cascade uses HAUS 2024; five option costs and most effect sizes are labelled placeholders. Read the outputs as comparisons of options with break-evens, not forecasts.

The app and pipeline load `data/processed/` (real, from `make ingest`); `data/mock/` is used only when a processed file is absent or `BEQAA_DATA=mock` (the tests). Badges: ✅ real · 🟡 partly real (some fields assumed, modelled or empty) · 🔴 mock · ⚪ missing (no mock exists, nothing is invented).

| Dataset | Status | What is real | What is still assumed, mock or missing |
|---|---|---|---|
| cadasters | ✅ real | 222 real admin-3 areas (COD-AB) in Baalbek, Hermel, Zahle, West Bekaa, Rachaya, with p-codes, Arabic names, area, centroid | nothing (2 zero-population areas dropped and logged) |
| population | 🟡 partly real | LRP 2026 totals by group, WorldPop 1 km spread, IOM DTM displaced; sums match LRP district totals | how each group is spread inside a district (modelled); registered vs unregistered Syrians (assumption) |
| facilities | 🟡 partly real | MoPH locator + PHC network list (97): 65 PHCCs and 29 hospitals placed in cadasters; `in_mophnetwork` is real; dated status for 4 facilities | PHCC positions are village centroids (1-5 km); capacity and ANC offering are assumptions; PHC functionality unknown |
| travel_time | 🟡 partly real | cadaster-to-facility minutes; cross-checked against the HDX accessibility file (Spearman 0.90 by district) | speeds are an assumption (straight line × 1.3 / 40 km/h); no road network |
| vulnerability | 🟡 partly real | IPC phase 3+ share by district (Sep 2026); VASyR 'below SMEB' by governorate (Syrian households, extra columns) | female-headed households, access barriers, insurance: no district source, left empty |
| official_severity | ✅ real | LRP Addendum JIAF / health severity classes for all 26 districts (hand-transcribed) | FSA composite printed for only 8 Severity-4 districts; other 18 empty |
| soil_sites | 🟡 partly real | CNRS-L/MoE Cr, total P, one Pb value for 5 Beqaa villages | no coordinates in the report: villages located by name at cadaster centroids; 4 villages unmatched; Cr(VI) share unknown |
| water_quality | removed | no public Beqaa well data | the mock dataset was deleted: water exposure is unknown for every cadaster (evidence gap); published studies are context only (`docs/EVIDENCE_TABLE.md`) |
| crop_transfer | ✅ real | Abi Saab et al. 2022 printed BAFs for Cr, Ni, Zn, Cu, Cd by crop and season | no Pb or As; pooled means only |
| interventions | 🟡 partly real | costs of 3 of 8 options derived from 48 sourced unit prices (`data/raw/costs`, `docs/COSTS.md`) | effects, reach and risk columns are assumptions; 5 options have no published cost (hub-spoke e-referral, vouchers, water truck, biochar, Cr(VI) speciation) |
| cascade_baseline | 🟡 partly real | HAUS 2024 reference cascade (any ANC, ANC4, facility delivery, postnatal; registered displaced Syrians, national) | other groups assumed equal to it (flagged); referral completion is a slider |
| staffing_referrals | removed | no public source | the mock dataset was deleted: referral completion and posts filled are scenario parameters (`docs/ASSUMPTIONS_PILOT.md`) |
| conflict_exposure | ✅ real | LRP conflict incidents per admin-3 (Oct 2023 - Jul 2025) | ACLED events for the last 30/90 days not loaded (API access returned HTTP 403) |
| governance_capacity | 🟡 partly real | WGI government effectiveness 29.9/100 and the LHF national NGO share, applied to every district | districts start identical (no district series is public); growth capped at 0.05 a year; transparent reporting is a scenario rule |
| funding_flows | ✅ real | OCHA FTS funding by year, cluster, recipient type | FTS cannot split national from international NGOs (LHF file does) |
| funding_requirements | ✅ real | OCHA FTS requirements and % funded (Flash Appeal 2026: 54%; Health cluster 60%) | nothing |
| agesex_by_district | 🟡 partly real | WorldPop 2025 age/sex 1 km, summed by district: population pyramids and demand shares (Why Beqaa) | modelled, not a census; not scaled to the LRP 2026 totals |
| damage_published | 🟡 to verify | 41 published damage figures (UN-Habitat BDDQA 2025, World Bank RDNA 2025, CNRS-L via Annahar 2026, IMPACT HSM) | extracted automatically: `to_verify_pdf`; governorate/district totals only; no 2026 Bekaa building-level data exists |
| beqaa_funding_proxy | 🟡 partly real | LHF health projects whose title names Bekaa or Baalbek-Hermel, by recipient type, 2024-26 (title keyword proxy; about 0-5% to national NGOs) | projects not naming Beqaa are missed; full budgets; no public 4W by governorate; the Beqaa theme KPI is therefore a proxy |
| beqaa_health_partners | 🟡 partly real | 49 organisations: 39 operate the MoPH-network PHCCs (MoPH list 16/04/2026, all Lebanese) plus INGOs/NNGOs/UN | `women_led` unknown for all (to verify on each organisation's own site); PHCC list may miss rows |
| esu (surveillance) | 🟡 partly real | MoPH ESU reported cases, 32 diseases, 2019 to Aug 2026, by month, caza, age and sex | notified cases, under-reported; Bekaa file = old Beqaa mohafaza; 2026 partial and late-2025 zeros are lag |
| informal_settlements | 🟡 old | IAMP Dec 2016: 135 cadasters, 184,966 people | OLD (2016); newer cadaster-level counts are not public |
| outreach, referral_payers, wash, capacity_waittime | 🟡 partly real | who runs outreach, who pays for referral, settlement water quality (72% faecal), PHCC counts | visit frequency, waiting times and referral completion NOT FOUND; no payer found for unregistered Syrians in hospital |
| evidence_pack, prices_pack, unit_costs, kpis | 🟡 partly real | 37 evidence rows, 20 prices (plus AUB lab prices), unit costs and KPIs | unverified prices stay sliders; no Lebanese Cr(VI), PPE or freight price |
| projects, riders | 🟡 to verify | 37 funded projects (desk search) and the rider cost per project | most project pages could not be opened; host project not confirmed |

**Registries (real, with source URLs and verified dates):** `funding_registry.csv` (22 funds), `org_registry.csv`, `sources.csv` (55+ sources), `state_capacity_sources.csv`, `workforce_sources.csv`. Rows marked `to_verify` are not yet checked against the primary source.

**Hand transcriptions** (`transcribed/`, two passes each, page references): UNHCR HAUS 2024 (appendix: why refugee households seek care), WHO sitreps, UNFPA appeal lines, LRP severity maps, CNRS soil, Abi Saab, VASyR/MSNA, UN-Habitat RMA, Citizen Budget. Both passes were made by one agent, so `checked=True` means "no typo found", not "verified by a second person".

**Assumptions that are not data** (all in the dashboard's assumptions log): Need Score anchors and weights, community local-fit and capture, escrow thresholds and ladder weights, scenario effect multipliers, access thresholds (30 / 60 min), the Syrian registered/unregistered split.

Details and coverage: `docs/DATA_STATUS.md` · what needs a person: `docs/MANUAL_STEPS.md`.

## Data we use and what it is for

One row per downloaded source (`data/registry/data_manifest.csv`; licences and refresh cadence are there). Real/mock status per dataset is in the table above.

| ID | Source | Publisher | Licence | What it feeds | Why we use it |
|---|---|---|---|---|---|
| D01 | Lebanon subnational administrative boundaries (COD-AB) | OCHA / HDX | CC BY-IGO | all (cadaster/district geometry and names) | Real district/cadaster names and polygons replace synthetic cadasters |
| D02 | Health facilities of Lebanon (OSM via HOT) | HOT / HDX | ODbL | M1 access; M2 capacity strain | Facility coordinates and types updated 2026-11; no 2026 open/closed status or capacity |
| D03 | LRP 2026 population package | GoL/UN LRP / HDX | CC BY | M1 demand; M2 clinical demand and equity groups | Official population by group (displaced Syrians; the gap to UNHCR records is the unregistered proxy S11) |
| D04 | IOM DTM Lebanon (admin 0-2) from API | IOM DTM / HDX | Other (see HDX page) | M1/M2 displaced population by district | Current IDP and returnee counts (S06) |
| D05 | IPC acute food insecurity: Lebanon | IPC / HDX | CC0 | M2 vulnerability (ipc3plus_share) | District-level IPC phase shares (S13) |
| D06 | FTS Lebanon requirements and funding | OCHA FTS / HDX | CC BY-IGO | Funding finder; dependency metric (money by recipient type) | Real funding by year and recipient (S19) |
| D07 | Lebanon accessibility indicators (PHC and hospital access) | HDX (CC BY-SA) | CC BY-SA | M1 cross-check of travel-time and access | Independent PHC/hospital access metrics to sanity-check our E2SFCA |
| D08 | WorldPop age and sex structures 2025 (1 km) | WorldPop / HDX | CC BY | M1 women 15-49 share (S09) | 100 m rasters (210 MB each) skipped; 1 km is enough for cadaster shares |
| S03 | WHO Lebanon Emergency Sitrep #23 (closed facilities map) | WHO EMRO | WHO | M1 closure scenario | Only facility-closure map found; closed facilities must be transcribed by hand |
| S08 | MoPH estimated resident population by age group and nationality 2024 | MoPH | MoPH | M1 demand weights (women 15-49 share by nationality) | URL from the catalog now returns 404; the LRP 2026 package (D03) already gives age/sex by nationality per governorate |
| S27 | CNRS-L/MoE post-war recovery report (Ch. II soil) | CNRS-L / MoE | as published | M4 exposure; M2 environment | Only Beqaa soil values (site values must be transcribed from Table 2.3) |
| S28 | Abi Saab et al. 2022 (Water 14(9):1437) | LARI / IWMI | CC BY | M4 crop transfer factors | PDF saved manually 2026-11-21; transcribe transfer factors |
| F07 | UNFPA Flash Appeal for Lebanon (Mar-Aug 2026) | UNFPA | as published | Funding registry F007; M5 cost lines | Maternal/SRH figures and appeal lines |
| D09 | LHF / CBPF project summary (Lebanon fund 71) | OCHA CBPF / HDX | CC BY | governance baseline (national NGO share of LHF) | Partner type per project: share to national NGOs by year |
| D10 | VASyR 2025 and MSNA 2025 (UNHCR/WFP/UNICEF; REACH/UN Women) | UNHCR / UN Women | not stated | M2 vulnerability | Governorate-level below-SMEB for Syrian households; district tables not published |
| D11 | WHO EMRO Lebanon sitreps #24-30 and UNICEF SitRep 5 | WHO / UNICEF | as published | facility status | Hospital damage/closure names (no locations); PHC totals only |
| D12 | UCDP GED Lebanon and HDX ACLED admin-2 monthly | UCDP / ACLED via HDX | CC BY-IGO (UCDP); ACLED terms (do not redistribute) | S1 escalation scenario | UCDP stops 2024; ACLED file is district x month |
| D13 | UN-Habitat Lebanon Rapid Municipal Assessment 2026; Citizen Budget 2026; WB WGI; IMF TA report | UN-Habitat / MoF / WB / IMF | as published | state capacity | National aggregates only; MoPH budget; SC01/W19 checks |
| D14 | UNHCR HAUS 2024 report (supplied by the team) | UNHCR Lebanon | not stated | appendix; cascade sources | Reasons refugee households seek care; ANC/delivery/PNC cascade for Syrian refugees; cost barriers |

Third-party PDFs (sitreps, VASyR, MSNA, HAUS, IMF, Abi Saab and others) are used to hand-transcribe values into `transcribed/` and are **not stored in git**: `python scripts/fetch_sources.py --restore-pdfs` re-downloads them from the URLs and sha256 hashes in each `data/raw/*/_provenance.json`. ACLED is not used until API access works (`docs/DEPLOY.md`).

## Principles (short)
Every number has a source and a status (`verified` / `assumption` / `mock`). Equity by group is reported in every model. Ranges and rank stability, not single numbers. Environmental claims carry rung a/b/c and nothing is ever tagged c without health data. One command rebuilds everything, with fixed seeds.
