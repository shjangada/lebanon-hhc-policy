# Headline audit: every number the memo or pitch may use, traced to a file and a source

Status: **ok** = traced to a file and source, no mock or fallback input; **ok (proxy / assumption)** = usable only with the stated label; **check** = the source has not been verified against the original (do not quote an effect size or figure until it has); **drop** = do not use. Files are under `data/processed` unless marked docs. "Placeholder" inputs (community priorities, five option costs, most effect sizes) are never headline numbers.

| Number | Where used | File | Source | Status |
|---|---|---|---|---|
| About 861,000 people, 222 cadasters | NARRATIVE beat 1, Why Beqaa | population.csv, cadasters.csv | LRP 2026 population package; COD-AB | ok |
| 1,030 conflict incidents (Oct 2023 to Jul 2025) | NARRATIVE, Why Beqaa | conflict_exposure.csv | LRP 2026 package (stops before the 2026 war) | ok |
| 65 centres, 29 hospitals | NARRATIVE, Why Beqaa, objections | facilities.csv | MoPH locator and PHC network list (positions = village centroids) | ok (proxy: positions) |
| 44.3% moderate or severe food insecurity (2024) | Why Beqaa facts | why_beqaa_facts.csv (W05) | FAO via World Bank API SN.ITK.MSFI.ZS | ok (national only) |
| 42% of cultivated area; Hermel about 40% in agriculture | Why Beqaa facts | why_beqaa_facts.csv (W01, W03) | FAO 2008 (c. 2000); UNDP story | check (reported, not re-read; the 42% is old) |
| Government pays 13.4% of health spending; WGI 29.9/100 | NARRATIVE, escrow | state_capacity_sources.csv (SC02, SC01) | K2P/UNICEF; World Bank API | ok |
| 37 inventoried funded projects; none tests soil or screens people | NARRATIVE, Funding today | projects.csv | desk search 2026-11-21; pages read through a summariser; most shortlisted pages blocked | check (state as "found in a desk search") |
| 38%-47% LHF share to national NGOs (2023-26) | NARRATIVE, KPI | lhf_national_ngo_share_by_year.csv | OCHA CBPF project summary | ok |
| 0% / 5.3% / 0% Beqaa-titled LHF health money to national NGOs | NARRATIVE, KPI, Funding today | beqaa_lhf_national_ngo_share_by_year.csv | title-keyword proxy, full budgets | ok (proxy) |
| 4.3% direct to local actors in 2025 vs 25% pledge | NARRATIVE | docs/sources S45 | ALNAP SOHS 2026 | check (reported) |
| Chromium 110-230 mg/kg (4 villages); lead 230 mg/kg (Bouday) | NARRATIVE, evidence | soil_sites.csv | CNRS-L / MoE Apr 2026, Table 2.3, two-pass transcription; TOTAL Cr | ok |
| Hazard quotient 0.27 to 280 | NARRATIVE, TRIGGERS, objections | m4_site_screen.csv | EPA defaults, Abi Saab 2022 factors, Cr(VI) share 0-1 | ok (modelled; range, not a point) |
| Lead screening level 200 ppm | TRIGGERS | docs/EVIDENCE_TABLE.md row 3 | EPA Jan 2024 guidance | check (see EVIDENCE_TABLE) |
| 72% faecally contaminated settlement samples (Jul 2026) | NARRATIVE, Care today, pitch | wash.csv | WaSH Sector / UNICEF SitRep No. 5 | ok |
| 15-20 L per person per day vs 35 L | Care today | wash.csv | WaSH Sector (2024) | ok |
| About 70% of wastewater untreated | NARRATIVE, pitch | evidence_pack.csv (E28) | CDR/MoEW strategic environmental assessment | ok (national; pack-verified) |
| Hepatitis A (Bekaa file): 690 (2023), 779 (2024), 270 (2025), 67 to Aug 2026 | NARRATIVE, Care today | esu_by_month.csv | MoPH ESU (reported; late-2025 zeros are lag; 2026 partial) | ok |
| Nitrate: 12 of 21 Bekaa-plain wells above 200 mg/L (2007-09); Baalbek-Hermel median 11 mg/L, max 137 | EVIDENCE_TABLE, pitch (context) | docs/EVIDENCE_TABLE.md rows 5-6 | Darwish 2011; Fahes 2025 | check (verify units and context before quoting) |
| Rider cost about $3,800-4,200; 0.5-0.9% of host budget | NARRATIVE, OPTIONS | riders.csv | AUB and K2P prices x ASSUMED sample counts | ok (assumption: counts) |
| Start-up about $33,000 (range $29,000-40,000) top site; $25 per household reached | OPTIONS, IMPLEMENTATION | unit_costs.csv, start_site | UNICEF catalogue, AUB, CHW pay x assumed counts | ok (assumption: counts; filters ex-works) |
| $2,600-8,500 per NOTIFIED case averted (10% coverage) | NARRATIVE, OPTIONS, objections | m6 (table) | ESU + Wolf 2022 RR (transferred) + prices | ok as an UPPER BOUND |
| Mobile unit $331k-1.21M per unit-year; CHW $12k-54k per 10 CHW-years | OPTIONS, interventions.csv | interventions.csv | per-consultation proxy (non-Lebanon) / job-posting pay | ok (proxy) |
| Break-evens: capture < 5.6%, local fit > 1.48 | NARRATIVE, OPTIONS, objections | breakeven.csv | scenario parameters (no published value) | ok (scenario) |
| Escrow thresholds 0.40 / 0.60 / 0.30; capacity 0.299 growing <= 0.05/yr | KPIs, IMPLEMENTATION | escrow_params.yaml, governance_capacity.csv | assumptions anchored to SC01 | ok (assumption) |
| First start site Saadnayel; stability 80% / 21% | NARRATIVE, FEASIBILITY, objections | start_site.rank_stability | scorer on processed data (tested against the docs) | ok |
| Access ranking stable to centre size (rho 0.997) | objections | m1_access.capacity_sensitivity | centre capacity assumed 200/300/400 | ok (assumption) |
| iCCM care-seeking RR 1.68; Lewin RR 0.86; Afshari, Ayaz, Das, Macfarlane | EVIDENCE_TABLE R01-R10 | docs/EVIDENCE_TABLE.md | abstracts read through a summariser | **do not quote effect sizes** (check) |
| Wolf 2022 risk ratios 0.50 / 0.66 / 0.70 / 0.53 | M6, evidence E01-E07 | evidence_pack.csv | pack-verified; transferred to hepatitis A and typhoid by assumption | ok with label (check against the paper) |
| 69 of 126 women farmworkers reported health problems | evidence E14, KPI reference | evidence_pack.csv | Agrimovement (Bekaa and Koura sample, self-reported) | ok with label; not a Beqaa baseline |
| Cord-blood antimony and nickel near farmland (n=74) | EVIDENCE_TABLE row 9 | evidence_pack.csv (E30-E32) | Beirut / Mount Lebanon, not Beqaa | ok with label; not a headline |
| EELI "106 pollutants" | none | evidence_pack.csv (E33) | Spanish study | drop |
| "90% of wastewater untreated (WHO)"; "30% of groundwater polluted by leachate"; "air pollution up 50%" | none | n/a | no primary source | drop |
| White phosphorus 1,858 ppm | none | n/a | it is TOTAL phosphorus | drop |
| Top 10 cadasters (9 Baalbek, 1 Hermel); core set = Tfail | NARRATIVE, FEASIBILITY | m2_need_score.csv, robust_core_set.txt | real inputs; district-reliable only; 61% of cadasters have an environment evidence gap | ok (resolution caveat) |

Mock data: none is entirely mock. Placeholders are listed in `docs/ASSUMPTIONS_PILOT.md`. Weak spots: unconfirmed host projects, abstract-only effect sizes, a 2016 settlement list, straight-line travel times.
