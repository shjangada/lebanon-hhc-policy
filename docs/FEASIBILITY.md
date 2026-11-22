# Feasibility ledger: grounding the Beqaa proposal in hard constraints (as of 21 Nov 2026)

**Rule for the whole project:** every statement or recommendation must (1) cite a fact or be labelled an assumption, (2) name the constraint it survives (money, security, power, staff, governance, legal status, data), and (3) be implementable by Dec 2030 by an institution that exists today.

---

## 0. Where the project stands (rewritten 2026-11-21; the earlier text described a mock-data build)

**Data.** No dataset is entirely mock (`io.any_mock()` is False; the red MOCK DATA watermark appears only if one is). Real or sourced: cadasters (222), official severity, crop transfer factors, conflict incidents (LRP, to Jul 2025), FTS and LHF funding, the MoPH facility list (97), WorldPop age/sex, the project inventory. Partly real or proxy: population (spread inside districts modelled), facilities (capacity assumed, centres at village centroids), travel time (straight line x 1.3 at 40 km/h), vulnerability (district IPC only), soil (5 villages), intervention costs (3 of 8 derived from sourced unit prices), cascade (HAUS 2024 reference; other groups assumed equal), governance (national anchors, identical districts). **Removed instead of kept as mock:** water quality (water exposure is unknown for every cadaster) and staffing (referral completion and posts filled are scenario parameters). The audit is `docs/HEADLINE_AUDIT.md`; the assumptions and what the pilot measures are `docs/ASSUMPTIONS_PILOT.md`.

**Built:** M1 access (E2SFCA, closure scenario, centre capacity 200/300/400 with a stable ranking), M2 Need Score (four domains; unsampled areas are *unknown*, not zero), M4 exposure screen, M5 options, community allocation, escrow ladder, robustness (six scenarios, regret, core set), **break-evens** (`breakeven.py`), health riders (`riders.py`), one-page dashboard with six sections (Why Beqaa, Funding today, Priority areas, Control of the money, Resilience, Funding sources) plus Methods. **Not built:** M3 network simulation, Workforce page, stepped-wedge/PDIA pilot page, OSM-road travel times, escrow overhead in the escrow-vs-direct comparison.

**What the current runs say (all conditional on stated assumptions; 125 tests pass):**
1. **Priority ranking:** on real inputs the top 10 cadasters are 9 in Baalbek and 1 in Hermel, driven by district-level IPC and conflict counts; 61% of cadasters have an environment evidence gap. No robust core set beyond a single cadaster (Tfail): district is the reliable resolution, cadaster a screening layer.
2. **Community-decided allocation loses to the status quo and to top-down at every tested value** when community priorities are placeholders. Best case (communities pick the most cost-effective option) it wins only if capture < 5.6% or the local-fit multiplier exceeds 1.48 (above the tested range 1.00-1.30). So the community-control claim is a design principle to be tested in a pilot, not a modelled advantage.
3. **Escrow:** with capacity starting at the national anchor (0.299) and growing at most 0.05 a year, the Union of Municipalities rung is reached about 2029 at +0.03 a year; local control of released money is about 33% until then (scenario, not forecast). The earlier "jump to MoPH by 2029" came from mock district data and is gone.
4. **Costs:** mobile-unit proxy $331k-1.21M per unit-year (4-8x the old mock); CHW $12k-54k per 10 CHW-years; a health rider on a funded project about $3,800-4,200 (central) or 0.5-0.9% of the project budget where known. Five option costs and most effect sizes remain labelled placeholders.
5. **Projects:** none of 37 inventoried funded projects tests soil or screens people for exposure (desk search; to confirm). That gap is the case for adding health to the funded water and agriculture channel (through the LHF window, with host projects optional).

---

**Start-site stability (`start_site.rank_stability`, 1,000 draws each).** (1) Weights perturbed by up to 25%: Saadnayel (Zahle) stays first in 98% of draws and Zahle holds first place in 98%. (2) Fully random weights: no single cadaster is stable (Saadnayel first in 30%, top 3 in 48%); first place goes to Zahle 40%, West Bekaa 36%, Baalbek 12%, Hermel 12%. (3) Leaving out one criterion at a time: Saadnayel is first in 4 of 7 cases. **Choose the district (Zahle) and a cluster, not one cadaster.**

## 1. The constraint baseline (hard facts)

| Constraint | Fact (date) | Source | Design rule it forces |
|---|---|---|---|
| **Money: humanitarian** | LRP 2026: $625.96M available = **39% of $1.62B**; Sep–Dec Addendum **17% funded** ($65.34M of $385.88M) (Jan–Sep 2026, pub. Nov 2026) | [LRP Funding Update Jan–Sep 2026](https://data.unhcr.org/en/documents/details/124737) | Assume ≤40% of any appeal-based budget materializes. Design modules that still work at 40%. |
| **Money: health sector** | Health Sector Sep–Dec 2026 requirement **$74.2M** (Q3 2026) | [Health Sector At a Glance Q3 2026](https://data.unhcr.org/en/working-group/19) | Our ask must be a small fraction of this, or ride on it. |
| **Money: public** | Government covers **13.4%** of total health spending (Oct 2025) | [K2P/UNICEF PHC financing memo](https://www.unicef.org/lebanon/media/13736/file/Primary-healthcare-financing-EN.pdf) | No recommendation may assume new MoPH budget by 2030. |
| **Money: municipal** | Independent Municipal Fund deficit **>$400M** (June 2026). Example small municipality: revenue fell from ~$105k (2018) to ~$14.9k (2024). Many can't pay "even one decent staff salary" (2025) | [LBCI, Jun 2026](https://www.lbcgroup.tv/news/news-bulletin-reports/943106/title/en?src=rss); [LBCI](https://www.lbcgroup.tv/news/news-bulletin-reports/881521/municipal-fee-hikes-in-lebanon-big-cities-gain-small-towns-struggle/en); [Arab Reform Initiative 2025](https://www.arab-reform.net/publication/empowering-lebanons-municipalities-amid-crisis/) | Municipalities can *govern* or *co-decide* funds; they cannot *finance* or reliably *administer* them alone. Target **Unions of Municipalities**, with an NGO or fund as fiduciary. |
| **Money: who gets it** | Lebanon = **most UN-dominated EU humanitarian portfolio (77% UN)** in 2025 (Feb 2026) | [VOICE analysis](https://voiceeu.org/publications/voice-analysis-dg-echo-2025-funding-distribution-among-partners-and-sectors.pdf) | Baseline for our "foreign intervention ↓" metric. |
| **Security** | "A ceasefire without peace": LAF recorded **7,700 Israeli violations** 26 Jun–9 Sep 2026; strikes in the Bekaa (Janta/Nabi Sheet area) on 16–20 Nov 2026; UNIFIL mandate expiring | [IISS, Nov 2026](https://www.iiss.org/publications/strategic-comments/2026/11/lebanon-a-ceasefire-without-peace/); [JNS, 19 Nov 2026](https://www.jns.org/news/israel-news/idf-strikes-hezbollah-missile-facility-in-lebanons-beqaa-valley) | Everything must be **pausable and resumable** (modular, no single point of failure, no large fixed assets in strike-prone areas). Renewed escalation is a named risk, not an afterthought. |
| **Attacks on health care** | WHO SSA since 2 Mar 2026: **129 deaths, 379 injuries** (by ~June). Attacks continued after the ceasefire | [WHO Sitrep #26](https://www.emro.who.int/images/stories/lebanon/Lebanon-Emergency-Sitrep-26-2026.pdf) | Don't rely on recruiting staff into exposed locations; protect staff data. |
| **Power** | EDL averages **~4–6 h/day**. Since 3 Nov 2026 EDL is **cutting power to public institutions with unpaid bills**. Private diesel generators supplied **~50%** of electricity in early 2026, at ~50–55¢/kWh | [L'Orient-Le Jour](https://today.lorientlejour.com/article/1544575/edl-gives-public-administrations-5-days-to-pay-bills-or-face-power-cuts.html); [Al Jazeera, 3 Nov 2026](https://aljazeera.com/news/2026/11/3/lebanon-cuts-power-to-public-bodies-as-electricity-crisis-deepens); [The National, Oct 2026](https://www.thenationalnews.com/news/mena/2026/10/14/wake-up-and-smell-the-diesel-multibillion-dollar-generators-industry-fuelling-lebanons-corruption/); [LBCI](https://www.lbcgroup.tv/news/news-bulletin-reports/950170/title/en?src=rss) | No design may require grid power. Digital tools must work **offline-first on phones**, with sync when connected. Budget for solar or generator at hubs. |
| **Workforce** | Since 2019, **40% of doctors and 30% of nurses emigrated**; 70% of public hospitals understaffed (Oct 2025). Family physicians absent in **86.3%** of PHCs. Rural PHCs meet staffing standards **46.4%** vs urban **73.6%** | [K2P/UNICEF](https://www.unicef.org/lebanon/media/13736/file/Primary-healthcare-financing-EN.pdf); Barake et al. Draft11S citing Hemadeh et al. 2020 | **No recommendation may depend on new doctors moving to the Beqaa.** Use rotation from hubs, task-shifting to nurses/midwives/CHWs, and remote consults. |
| **Legal status** | Only **17%** of Syrians aged 15+ hold legal residency (2025). UNHCR records: **889,625** (30 Jun 2026) vs LRP planning figure **1.12M**. UNHCR phased out subsidized PHC consultations at three PHCs, leaving **~40,000 refugees** without access (2025) | [UNHCR Annual Results Report 2025](https://www.unhcr.org/sites/default/files/2026-06/unhcr-annual-results-report-2025-lebanon.pdf); [UNHCR health factsheet](https://www.unhcr.org/sites/default/files/2025-10/UNHCR%20LBN_Health%20Factsheet%20.pdf); [Enab Baladi, Oct 2026](https://english.enabbaladi.net/archives/2026/10/lebanon-extends-residency-waiver-for-syrian-students-to-enroll-in-school/) | Any service that requires ID, registration or a tracked record **excludes most Syrian workers**. Design anonymous or community-ID options and say so. |
| **Displacement** | 329,686 IDPs; 877,203 returned (29 Sep 2026); ~304,500 outside their area of origin (31 Oct) | [IOM DTM Round 118](https://dtm.iom.int/operations/lebanon-crisis); [Inter-Agency Update #1](https://reliefweb.int/report/lebanon/lebanon-inter-agency-response-update-31-october-2026) | Demand is moving. Recompute access quarterly, not once. |
| **Data systems** | MoPH uses **DHIS2** for disease surveillance (since 2017). A MoPH/UNICEF digital health strategy targets 2030. No public facility-level closure list or referral-completion data found | [Youssef et al. 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC8957192); [MoPH/UNICEF strategy](https://www.unicef.org/lebanon/media/13696/file/Digital%20health%20transformation%20strategy%20EN.pdf) | Build on DHIS2 rather than a new system. Referral completion is a **pilot indicator to collect**, not existing evidence. |
| **Food & livelihoods** | **1.05M** in IPC 3+ (Sep 2026–Feb 2027), **1.15M** by mid-2027; Baalbek-Hermel flagged (13 Nov 2026) | [WFP/IPC](https://www.wfp.org/news/food-insecurity-persists-lebanon-fragile-conditions-stall-recovery-efforts-new-analysis-shows) | Cost barriers are rising. Keep vouchers and transport support in scope. |

---

## 2. The feasibility filter (apply to every recommendation)

A recommendation stays in the memo only if it passes all eight. Add these as columns in `interventions.csv` and as a filter in M5.

| # | Test | Pass looks like |
|---|---|---|
| F1 | **No new public money needed by 2030** | Funded by an existing donor window (LHF, LFF, EU civil-society window, LEAP, UNDP/WB GATE grants) |
| F2 | **Pausable under escalation** | Can suspend and restart within weeks; no fixed asset that's lost if a site is struck |
| F3 | **Runs on ≤6 h grid power** | Offline-first, solar or generator budgeted |
| F4 | **No dependence on new doctors relocating** | Uses existing staff, rotation, task-shifting, CHWs |
| F5 | **Uses an existing institution** | MoPH PHC network, Health Sector, Unions of Municipalities, LHSP/MoSA, LHF/LFF; no parallel structure (LRP principle) |
| F6 | **Reaches people without residency** | No ID requirement, or an explicit workaround |
| F7 | **Cost fits a real funding window** | Ask ≤ a plausible share of a named window, with a sourced unit cost |
| F8 | **Measurable with data that exists or that the pilot collects** | Indicator named, with a source or a collection plan |

---

## 3. Component-by-component verdicts (by Dec 2030)

| Component | Verdict | What's realistic | What isn't | Evidence and precedent |
|---|---|---|---|---|
| **Beqaa Need Score** (M2) | ✅ Feasible, rescoped | Quarterly score for one district's PHCs, using 6–8 indicators the PHC network already reports, published alongside the Health Sector severity index | A real-time national clinic-level score; MoPH adopting it nationally by 2030 | DHIS2 exists; sector severity index uses thresholds (2024 annex); Barake left the formula undefined |
| **Access map** (M1) | ✅ Feasible now | Quarterly recompute with DTM rounds and situation-report closure totals | Facility-level live status (no public list) | DTM, WorldPop, OSM all available |
| **Mobile maternal units** | ⚠️ Feasible if attached to PHC hubs | 1–3 units in top-ranked towns, run by an existing partner, scheduled from a hub, pausable | Standalone NGO units outside MoPH referral lines (parallel structure; dependency) | UNFPA deployed 9 mobile units in 2026; MSF ran Bekaa mobile clinics from Mar 2026. **Unit cost is mock: get a real quote** |
| **Hub-and-spoke + referral tracking** | ⚠️ Partly | One hub (e.g., a Baalbek public hospital) with 6–10 spoke PHCs; referral log on phones (DHIS2 tracker/ODK), offline-first; counter-referral by SMS or WhatsApp | A national e-referral system or EHR by 2030 | Needs F3 (power) and F6 (no ID). Data protection for undocumented patients is a must |
| **CHWs via women's organizations** | ✅ Feasible | 10–20 CHWs per district doing antenatal follow-up, referral escorts and risk messaging; stipend model | Paid employment of Syrian CHWs where labor law restricts it (check legal route) | IRC trained ~500 refugee outreach volunteers for NCD care ([GHSP 2017](https://www.ghspjournal.org/content/5/3/495)); Zaatari 2006 on women's orgs |
| **Cr(VI) speciation + soil/water screening** | ✅ Feasible now (≤$1.5k) | Test the CNRS-L Beqaa hotspots (Chemstar, Rayak, Bouday; second wave after the scorer's first sites) through an AUB lab | Area-wide screening without a funder | **Lab cost is mock: get an AUB quote**. Settles the key uncertainty in M4 |
| **Washing-water point for field workers** | ⚠️ Feasible short-term | One municipality or cooperative pilot, through the WASH sector | Sustained service without a recurring funder (WASH reached only 16% of its target, Jan–Sep 2026) | [WASH At a Glance](https://data.unhcr.org/en/documents/download/124668) |
| **Sunflower + biochar plots** | ⚠️ Research pilot only | Trial plots with AUB and a Cooper Union adviser; measure soil change | Any claim of a health effect by 2030 | Possible funding: UNDP/WB **$20M Climate-Smart Matching Grants** (GATE, launched 13 Oct 2026) — check eligibility ([UNDP](https://www.undp.org/node/609146)) |
| **Escrow / funding switch** | ⚠️ Feasible **as a window inside an existing pooled fund**, not as a new fund | A ring-fenced Beqaa window in LHF or LFF with a need floor plus a capacity tranche keyed to process indicators | A new escrow vehicle set up, capitalized and trusted by 2030; full MoPH administration by 2030 | LFF (World Bank MDTF since Dec 2020, civil-society oversight under 3RF); LHF channels to national NGOs; Cochrane 2021: pay-for-performance has **mixed** effects, so keep the need floor and use process triggers |
| **Community-decided allocation** | ⚠️ Feasible via an existing process | Use UNDP–MoSA LHSP's Maps of Risks and Resources (participatory municipal plans, 251 most-vulnerable localities) to set priorities inside the pilot | Claiming it improves governance or social cohesion | 3ie WP30 (2018): CDD improves facilities, **not** cohesion or governance. Mock results currently show it underperforming, so make it a **test arm** |
| **State capacity ↑ / foreign intervention ↓** | ⚠️ Measurable, but modest by 2030 | Raise the share of *pilot* funds managed by Lebanese entities (national NGOs, Unions of Municipalities) from a baseline to a target, e.g. ≥50% by 2030 (target = assumption) | Reversing the national 77%-UN pattern; MoPH running the system on its own budget | VOICE 77% UN; government 13.4% of health spending |
| **Moving doctors to high-need areas** | ❌ As relocation · ✅ as rotation | Hub rotation days, task-shifting, remote consults, hardship stipends tied to the Need Score | Permanent redistribution of physicians | 40% of doctors emigrated; 129 health-worker deaths in 2026 |

---

## 4. A 2030 roadmap with gates

| Phase | When | Scope | Cost order | Go / pause gate |
|---|---|---|---|---|
| **0. Start** | Dec 2026–Mar 2027 | Cr speciation at 3 hotspots; partner MOUs (AUB lab, one hub hospital, one women's org, one Union of Municipalities); data pull (DTM, IPC, VASyR 2026, Health Sector) | $1k–$10k | Lab results in hand; ≥2 MOUs |
| **1. Pilot** | 2027 | One district (top-ranked by M2, robust across weightings): 1 hub + 6–10 PHCs, quarterly Need Score, phone referral log, 10–20 CHWs, 1 mobile unit if needed | $150k–$400k (to be sourced) | Referral completion measured; ≥80% of PHCs reporting; no security pause >8 weeks |
| **2. Stepped-wedge** | 2028 | Add 2 districts in sequence (comparison built in); community-decided arm vs top-down arm | Scale by district | Indicators improve vs not-yet-started districts |
| **3. Embed** | 2029–2030 | Need Score published with the Health Sector severity index; Beqaa window inside LHF/LFF with tranche rules; admin share shifted toward Lebanese entities | Through existing pooled funds | Lebanese-managed share ≥ target; process indicators stable |

**Pause rules (state them in the memo):** escalation in pilot districts, fewer than X% of PHCs open, or funding below 40% of plan triggers suspension of fixed activities while CHWs and phone follow-up continue.

---

## 5. Concrete changes for the repo

Status: items 1, 2, 4, 5, 6 and 7 are implemented (feasibility columns and filter; escrow recalibration with a renewed-escalation scenario and Union-of-Municipalities ceiling; power and conflict-exposure columns with a facility-pause scenario; community allocation framed as pilot test arms with a sensitivity grid; citations and source catalog). Item 3 (real unit costs and quotes) is open.

1. **(done)** Add F1–F8 columns to `interventions.csv` (`needs_new_public_money`, `pausable`, `grid_power_dependent`, `needs_new_doctors`, `existing_institution`, `requires_id`, `funding_window`, `indicator_source`) and filter on them in M5 and the dashboard.
2. **(done)** Recalibrate `governance_capacity` projections: cap year-on-year gains (e.g., ≤0.05/yr) and default the 2030 administrator to national NGO / Union of Municipalities, not MoPH. Add a "renewed escalation" scenario that drops capacity.
3. Replace mock costs with sourced unit costs: UNFPA/WHO appeal lines for mobile units, an AUB quote for speciation, WASH sector costs for water trucking, IRC/UNFPA stipends for CHWs.
4. **(done)** Add a **power** column to facilities (grid / generator / solar) and a **security** exposure flag (distance to 2026 strike locations) to M1/M2.
5. **(done)** Change the community-allocation framing in the dashboard from "result" to "pilot test arm", and show the assumption sensitivity (capture 0.1–0.4, local fit 1.0–1.3).
6. **(done)** Verified the `Mansuri & Rao 2013` citation (World Bank Policy Research Report, title is "Localizing Development: Does Participation Work?", DOI 10.1596/978-0-8213-8256-1) and added it as S35; the 3ie WP30 and Cochrane 2021 citations are S26 and S25 in `sources.csv`.
7. **(done)** Loaded `data_catalog.csv` (30 sources) into `data/registry/sources.csv`.

---

## 6. Wording guardrails for the memo and pitch

| Avoid | Say instead |
|---|---|
| "Redistribute doctors to the Beqaa" | "Rotate hub specialists to spoke clinics and shift routine antenatal care to nurses, midwives and CHWs" |
| "Build a national e-referral system" | "Track referrals on phones at one hub and its clinics, offline-first, feeding DHIS2" |
| "Transfer control to MoPH by 2030" | "Raise the share of pilot funds managed by Lebanese entities to ≥50% by 2030, with MoPH co-governance" |
| "Community control improves outcomes" | "We test community-set priorities against top-down allocation in a stepped-wedge pilot" |
| "Soil contamination is harming health" | "Soil levels at three Beqaa sites exceed screening thresholds; whether chromium is the toxic form is unknown, and a ≤$1,500 test settles it" |
| "Create an escrow fund" | "Open a ring-fenced Beqaa window in an existing pooled fund, with a guaranteed need floor and capacity-based tranches" |
| "Stability will allow…" | "If escalation resumes, fixed activities pause and CHW and phone follow-up continue" |
