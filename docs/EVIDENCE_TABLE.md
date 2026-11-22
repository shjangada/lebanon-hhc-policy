# Evidence table: one row per claim the recommendation depends on

Rung: **(a)** environmental finding · **(b)** plausible exposure pathway · **(c)** demonstrated health effect. Geography: Beqaa (five districts) / other Lebanon / international. Verification: `verified` = value in the repo, transcribed in two passes or read from a primary file; `modelled`; `reported` = number from the cited source as reported to the team, **not re-read here** (check before quoting); `to_verify`. **No row below is rung (c) for Beqaa: no health effect has been shown.**

| # | Claim | Rung | Geography | Source | Verification |
|---|---|---|---|---|---|
| 1 | Total chromium 110-230 mg/kg in soil in 4 sampled villages (Chmestar, Ksarnaba, Rayak, Bouday) | a | Beqaa (villages located by name; no coordinates in the report) | CNRS-L / MoE post-war soil report, Apr 2026, Table 2.3 (`data/processed/soil_sites.csv`) | verified (two passes) |
| 2 | A crop-soil exposure route for chromium is plausible: child hazard quotient 0.27 to 280 depending on the Cr(VI) share (0 to 1); the form decides | b | Beqaa (model) | M4 screen (`m4_site_screen.csv`), EPA defaults, Abi Saab et al. 2022 transfer factors | modelled; Cr(VI) share not measured |
| 3 | Lead 230 mg/kg at Bouday, above the 200 ppm EPA residential screening level | a (screening exceedance); b in the model | Beqaa | CNRS-L / MoE 2026; EPA 2024 screening level | verified value; level to_verify_primary |
| 4 | Total phosphorus 146-1,858 mg/kg (highest in Rayak). **Total P is not white phosphorus** and cannot establish munition exposure | a only | Beqaa | CNRS-L / MoE 2026 | verified value; never state as WP |
| 5 | Nitrate: 12 of 21 Bekaa-plain wells exceeded 200 mg/L (2007-09) | a | Beqaa (old) | Darwish et al. 2011, Agric. Water Manage. 99:74-84 | to_verify (abstract read through a summariser) |
| 6 | Nitrate in Baalbek-Hermel samples: median 11, max 137 mg/L (Lebanese standard 45), n=41, Jul-Oct 2023; Beqaa governorate n=2 (unusable) | a | Baalbek-Hermel | Fahes et al. 2025, Sci. Rep. 15:10539 | to_verify (summariser; mixed sample types) |
| 7 | About 70% of generated wastewater is discharged untreated; private wells supply 33% of water | a | Lebanon (national) | CDR / MoEW strategic environmental assessment of the National Water Sector Strategy | reported (not re-read); the "90% (WHO)" figure is NOT used |
| 8 | Bebnine: women dissatisfied with water quality reported worse health; household water treatment protective against child diarrhoea | b / c | North Lebanon (Akkar), about 2009-13 | Habib et al., Women & Health 2013; companion study (EcoHealth) | to_verify: the "42%" figure is not in the abstract; do not quote it |
| 9 | Toxic metals detected in cord blood (n=74); living near agricultural land was associated with higher antimony (p=0.033) and nickel (beta=0.118, p=0.011); detection is not a health effect | b | Beirut / Mount Lebanon (not Beqaa) | EELI correlates paper, Sci Rep 2026 (see E30-E32). The earlier 'IJHEH 2026, 106 pollutants' citation is a Spanish study and is removed (E33) | pack-verified: spot-check |
| 10 | Women in agriculture have household and occupational pesticide exposure routes; women's exposure is often under-estimated | b | International (no Beqaa study found) | FAO 2023 Status of Women in Agrifood Systems; Deziel et al. 2015 EHP | reported |
| 11 | Rural women do a major share of agricultural labour in Lebanon, often unrecognised and low paid | b (occupational) / context | Lebanon | FAO 2021 Country Gender Assessment; UN Women 2022, 2024 | reported |
| 12 | Lack of clean water raises menstrual and postpartum hygiene problems and infections | b | no Lebanon source found | WASH literature (none cited) | assumption: find a UNFPA/UNICEF WASH-MHM source |
| 13 | Landfill leachate contaminates about 30% of groundwater; air pollution up 50% | not used | Lebanon | advocacy sources (AFSC, UN) | **not verified: dropped** |
| 14 | Direct funding to local actors: 4.3% in 2025 vs a 25% Grand Bargain pledge | context | global | ALNAP SOHS 2026 ch.4 (S45) | reported |
| 15 | LHF share of project budgets to national NGOs: 38% (2023), 38% (2024), 44% (2025), 47% (2026, partial year) | context | Lebanon (one pooled fund) | OCHA CBPF project summary (`lhf_national_ngo_share_by_year.csv`) | verified (file) |
| 16 | Beqaa-titled LHF health projects: 0%, 5.3%, 0% to national NGOs (2024, 2025, 2026) | context | Beqaa (proxy) | title keywords only; full budgets (`beqaa_lhf_national_ngo_share_by_year.csv`) | proxy: projects not naming Beqaa are missed |
| 17 | Government pays 13.4% of total health spending; WGI government effectiveness 29.9/100 (2025) | context | Lebanon (national) | SC02 (K2P/UNICEF), SC01 (World Bank) | SC01 verified (API); SC02 verified |
| 18 | None of 37 inventoried funded projects tests soil contamination or screens people for exposure | context | Beqaa | project inventory (desk search, 2026-11-21) | to_verify: pages read through a summariser; several blocked |
| 19 | CHW home visits raised any-ANC by 10.5 points (CI 4.2 to 16.9) in Afghanistan; null on 4+ visits in a Tanzania trial | context (effect size) | international | Edmond 2018, BMC Medicine; Geldsetzer 2019, PLoS Med | to_verify (read through a summariser) |

What would change the response: a Cr(VI) speciation test in the 4 villages (rows 1-2: decides whether the response is monitoring or protection); measured water nitrate in the wells the funded projects serve (rows 5-7); maternal and cord-blood biomonitoring near the sampled villages (rows 9-10: the route from (b) to (c)).


## Evidence pack (E01-E37, merged 2026-11-21; corrections applied)
Source: `data/raw/evidence/evidence.csv` (`data/processed/evidence_pack.csv`; each row has a URL there). The `verified` column is the pack's own flag (the page or paper was opened by its author; **spot-check before quoting**). Geographies and notes below apply the latest verification corrections:
the Agrimovement survey is a **Bekaa and Koura** sample; the cord-blood correlates study is **n=74, Beirut / Mount Lebanon** (living near farmland: antimony p=0.033, nickel beta=0.118 p=0.011); the "106 pollutants" paper is **Spanish** and is excluded;
Salvatore 2015 (-51.3%, CI -81.3 to +26.8) is **not significant**; soil chromium is **total Cr** (no Cr(VI) data exist). Rung (c) rows E01-E07 are transferred diarrhoea effects in low- and middle-income countries; rows E12-E16 are self-reported symptoms or injuries, not linked to a measured exposure.

| id | claim | figure | rung | geography | verified | note |
|---|---|---|---|---|---|---|
| E01 | Point-of-use filtration reduces child diarrhoea risk | 0.50 (0.41-0.60) | c | international | yes |  |
| E02 | Chlorination (household) reduces child diarrhoea risk | 0.66 (0.56-0.77) | c | international | yes |  |
| E03 | Solar water disinfection reduces child diarrhoea risk | 0.63 (0.50-0.80) | c | international | yes |  |
| E04 | Improved drinking water supply on premises with higher water quality (vs unimproved source) reduces diarrhoea risk | 0.48 (0.26-0.87) | c | international | yes |  |
| E05 | Sewer connection (vs unimproved sanitation) reduces diarrhoea risk | 0.53 (0.30-0.93) | c | international | yes |  |
| E06 | Sanitation interventions overall reduce diarrhoea risk | 0.76 (0.61-0.94) | c | international | yes |  |
| E07 | Promotion of handwashing with soap reduces diarrhoea risk | 0.70 (0.64-0.76) | c | international | yes |  |
| E08 | Educational/behavioural pesticide-safety interventions improve knowledge and attitudes but are less effective at changing behaviour and reducing exposure; multifaceted interventions moderately effective; no studies of engineering/technological or legislation/enforcement interventions found | 31 studies (9 RCTs, 22 quasi-experimental) | b | international | yes |  |
| E09 | CHW home-based education (3 sessions) and child urinary total DAP metabolites, adjusted | -51.3% (95% CI -81.3 to +26.8), p=0.14 | b | international | yes | NOT significant: the confidence interval includes zero (n=116 families). |
| E10 | Community-wide intervention did not reduce OP exposure in farmworker children (null result) | p=0.21 (urinary metabolites, intervention vs control, year-adjusted); p=0.49 (house/vehicle dust) | b | international | yes |  |
| E11 | Akkar smallholder farmers using no protective gear | 37.7% | b | other Lebanon | yes |  |
| E12 | Akkar farmers reporting acute symptoms (respiratory irritation, skin issues) after pesticide use | 67.5% (102/151) | c | other Lebanon | yes |  |
| E13 | Survey sample of Syrian refugee women farmworkers | 126 | c | Bekaa and Koura sample (not Beqaa only) | yes | Agrimovement survey; self-reported; not linked to a measured exposure. |
| E14 | Women farmworkers reporting health problems | 69 of 126 | c | Bekaa and Koura sample | yes | self-reported health problems, not linked to a measured exposure |
| E15 | Women farmworkers reporting workplace injuries (mild and acute) | 26 of 126 | c | Bekaa and Koura sample | yes | self-reported injuries |
| E16 | Women farmworkers who received medical support; coverage of costs | 24 of 126; covered at most 30% of financial expenses | c | Bekaa and Koura sample | yes |  |
| E17 | Women farmworkers living in tents in informal settlements | 94 of 126 | b | Bekaa and Koura sample (94 of 126 in the executive summary vs 90 of 120 in Section 4) | yes |  |
| E18 | Average daily wage, men vs women farmworkers | 900,000 vs 600,000 | b | Bekaa and Koura sample | yes |  |
| E19 | Syrian refugees aged 15+ with legal residency | 22% | b | other Lebanon | secondary | as quoted by Agrimovement; VASyR not opened: secondary |
| E20 | Pesticide use intensity in Lebanon vs global average | 6.5 vs 2.26 (Lebanon was 4 in 1990) | a | other Lebanon | yes |  |
| E21 | Irrigation water with <2 log E. coli CFU/100 mL: no pathogens (E. coli, Salmonella, parasite eggs) detected on vegetables, any irrigation method | 0 pathogens detected | b | Beqaa | yes |  |
| E22 | With >2 log E. coli CFU/100 mL, parasitic contamination by irrigation method | 8.33% (sprinkler and surface-irrigated vegetables) vs 2.78% (drip-irrigated root crops) | b | Beqaa | yes |  |
| E23 | Pesticide residues in Lebanese-grown apples | 212 samples; 77% with residues; 61% > MRL; 16% residues below MRL; 23% no residues | a | other Lebanon | yes |  |
| E24 | Groundwater nitrate contamination in Upper Litani Basin is 'significant, widespread and persistent'; exceeds drinking-water limits in many parts of the basin | no % reported in abstract | a | Beqaa | yes | Assaf & Saadeh: no percentage of wells over the limit is given: do not quote one |
| E25 | Nitrate in groundwater wells along a Litani River-to-eastern-divide transect | 12 of 21 wells >200 mg/L nitrate; only 1 of 21 suitable for drinking; 8 mildly contaminated | a | Beqaa | yes | Darwish et al. 2011: 200 mg/L is a lower bound, NO3 vs NO3-N unconfirmed: verify units and context in the paper before quoting |
| E26 | Share of 10 Lebanese rivers exceeding FAO irrigation limit for E. coli (126/100 mL) | 60% | a | other Lebanon | yes |  |
| E27 | Share of 10 rivers exceeding FAO upper limit for faecal coliforms (1000/100 mL) | 40% (El Kabir, Kadisha, Antelias, El Awali) | a | other Lebanon | yes |  |
| E28 | Share of generated wastewater discharged untreated | ~70% | a | other Lebanon | yes |  |
| E29 | Private wells share of national water supply | 33% (~631 MCM/yr); springs 31% (~593 MCM/yr); public wells 18% (344 MCM/yr) | a | other Lebanon | yes |  |
| E30 | All toxic heavy metals detected in Lebanese cord blood; Pb and Hg among highest | Pb median 5.45 ug/L (p95 22.4); Hg median 0.7 ug/L (p95 2.01) | b | Beirut / Mount Lebanon (n=74), not Beqaa | yes | Correlates paper (Sci Rep 2026), n=74, Beirut / Mount Lebanon: detection is not a health effect |
| E31 | Residential proximity to agricultural land associated with higher cord blood antimony (bivariate) | Mann-Whitney U z=-2.135, p=0.033 | b | Beirut / Mount Lebanon (n=74), not Beqaa | yes |  |
| E32 | Residential proximity to agricultural land associated with higher cord blood nickel (multivariate) | beta=0.118, p=0.011 (Ni model R2=0.423) | b | Beirut / Mount Lebanon (n=74), not Beqaa | yes |  |
| E33 | 2026 IJHEH '106 pollutants in cord blood' paper is a SPANISH (La Palma) study, not Lebanese: 106 pollutants quantified; maternal smoking shaped mixtures; SGA neonates of smokers had distinct PAH/OCP/low-chlorinated PCB/Pb mixture | n=471 neonates; 106 pollutants | b | Spain (La Palma): NOT Lebanese evidence | yes | EXCLUDED from the Lebanon evidence (it was cited as 'EELI 106 pollutants') |
| E34 | Soil total Cr, Chmestar (3 samples) | 110; 230; <LOD (50) | a | Beqaa | yes | TOTAL chromium: the CNRS-L report has no Cr(VI) data |
| E35 | Soil total Cr and Pb, Bouday | Cr: 140 (1 of 6; other 5 <LOD 50); Pb: 230 (single hotspot) | a | Beqaa | yes | TOTAL chromium |
| E36 | Soil total Cr, Ksarnaba (7 samples) | 130; 170 (other 5 <LOD 50) | a | Beqaa | yes | TOTAL chromium |
| E37 | Soil total Cr and total P, Rayak (5 samples) | Cr: 130; 150; 220; <LOD; 140. Total P: 1672; 722; 564; 1858; 976 | a | Beqaa | yes | TOTAL chromium; total P is not white phosphorus |

## Research pass 2026-11-21: CHW case management and pesticide protection
Read through abstracts only (Europe PMC abstracts relayed by a summarising tool; full texts, PMC and Cochrane pages were blocked), so **do not quote any effect size below until it has been checked against the abstract or full text**. Rungs: these are effect studies elsewhere (international) unless stated; the Lebanese rows are self-reported or qualitative.

| # | Claim | Figure | Rung | Geography | Source | Status |
|---|---|---|---|---|---|---|
| R01 | iCCM (diarrhoea, pneumonia, malaria treated by lay workers): care-seeking improved | RR 1.68 (1.24-2.27), moderate certainty | c (transferred) | international (7 studies) | Oliphant et al. 2021, Cochrane | abstract only: do not quote effect sizes |
| R02 | iCCM: appropriate treatment | RR 0.96 (0.77-1.19), very low certainty: no clear difference | c (transferred) | international | Oliphant et al. 2021 | abstract only: do not quote effect sizes |
| R03 | iCCM: mortality (as reported) | hazard ratios neonatal 1.01 (0.73-1.28), infant 1.02 (0.83-1.26), under-five 1.18 (1.01-1.37), very low certainty | c (transferred) | international | Oliphant et al. 2021 | abstract only: do not quote effect sizes; do not present as evidence of benefit |
| R04 | Community-based interventions for childhood diarrhoea: ORS use +160%, zinc +80%, antibiotics for diarrhoea -75% | no CIs in the abstract | b/c (transferred) | international | Das et al. 2013, BMC Public Health | abstract only: do not quote effect sizes (study count not confirmed) |
| R05 | Lay health workers: child morbidity RR 0.86 (0.75-0.99); child mortality RR 0.75 (0.55-1.03); care-seeking 1.33 (0.86-2.05) | abstract does not mention diarrhoea; 82 studies, 55 in high-income countries | c (transferred) | international | Lewin et al. 2010, Cochrane | abstract only: do not quote effect sizes |
| R06 | Pesticide-safety interventions: educational ones improve knowledge and attitudes but less often behaviour; multifaceted ones are moderately effective; no engineering or legislative studies found | no effect sizes in the abstract; 31 studies (9 RCTs) | b | international | Afshari et al. 2021, PLoS ONE (a review, not Cochrane) | abstract only: do not quote effect sizes |
| R07 | Educational interventions for agricultural workers | Hedges g: knowledge 0.890, behaviour 0.707, risk perception 0.377 (no CIs in the abstract) | b | international (38 studies) | Ayaz et al. 2022 | abstract only: do not quote effect sizes |
| R08 | Personal protective equipment reduces dermal exposure; compliance is poor | no effect size | b | international | Macfarlane et al. 2013 (narrative review; volume and issue unconfirmed) | abstract only: do not quote effect sizes |
| R09 | Akkar farmers: WhatsApp video training improved most; 37.7% used no protective gear; 67.5% reported acute symptoms | RCT n=133 (no numbers in the abstract); survey n=151 | b / c (self-reported) | other Lebanon (Akkar) | Akkouch et al. 2025 | abstract only: do not quote effect sizes |
| R10 | Syrian refugee agricultural workers' pesticide exposure in Lebanon | non-empirical framework paper; no PPE or legal-status numbers | context | Lebanon | Noory et al. 2024 | abstract only: do not quote |

**Not found** (so the matching assumptions stay sliders): the WHO/UNICEF iCCM joint statement text; CHW first-aid or injury care; referral completion after a CHW referral; any Lebanon or Syrian-refugee CHW outcome evidence; a trial of protective gear against urinary pesticide metabolites; effect sizes from the Afshari review's full text. **So "CHWs can handle most cases" has no direct support in Lebanon and only mixed support elsewhere: it stays a slider, and the pilot measures it.**
