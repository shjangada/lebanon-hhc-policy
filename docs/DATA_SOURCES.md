# Data sources with access dates

From `data/registry/data_manifest.csv` and each `data/raw/*/_provenance.json` (retrieved date; the manifest rows were retrieved 2026-11-21 unless the file says otherwise). Third-party PDFs are not stored in git: `python scripts/fetch_sources.py --restore-pdfs`.

| ID | Dataset | Source | Publisher | Licence | Retrieved | Feeds |
|---|---|---|---|---|---|---|
| D01 | cadasters | Lebanon subnational administrative boundaries (COD-AB) | OCHA / HDX | CC BY-IGO | 2026-11-21 | all (cadaster/district geometry and names) |
| D02 | facilities | Health facilities of Lebanon (OSM via HOT) | HOT / HDX | ODbL | 2026-11-21 | M1 access; M2 capacity strain |
| D03 | population | LRP 2026 population package | GoL/UN LRP / HDX | CC BY | 2026-11-21 | M1 demand; M2 clinical demand and equity groups |
| D04 | population | IOM DTM Lebanon (admin 0-2) from API | IOM DTM / HDX | Other (see HDX page) | 2026-11-21 | M1/M2 displaced population by district |
| D05 | vulnerability | IPC acute food insecurity: Lebanon | IPC / HDX | CC0 | 2026-11-21 | M2 vulnerability (ipc3plus_share) |
| D06 | funding_flows | FTS Lebanon requirements and funding | OCHA FTS / HDX | CC BY-IGO | 2026-11-21 | Funding finder; dependency metric (money by recipient type) |
| D07 | travel_time | Lebanon accessibility indicators (PHC and hospital access) | HDX (CC BY-SA) | CC BY-SA | 2026-11-21 | M1 cross-check of travel-time and access |
| D08 | population | WorldPop age and sex structures 2025 (1 km) | WorldPop / HDX | CC BY | 2026-11-21 | M1 women 15-49 share (S09) |
| S03 | facilities | WHO Lebanon Emergency Sitrep #23 (closed facilities map) | WHO EMRO | WHO | 2026-11-21 | M1 closure scenario |
| S08 | population | MoPH estimated resident population by age group and nationality 2024 | MoPH | MoPH | 2026-11-21 | M1 demand weights (women 15-49 share by nationality) |
| S27 | soil_sites | CNRS-L/MoE post-war recovery report (Ch. II soil) | CNRS-L / MoE | as published | 2026-11-21 | M4 exposure; M2 environment |
| S28 | crop_transfer | Abi Saab et al. 2022 (Water 14(9):1437) | LARI / IWMI | CC BY | 2026-11-21 | M4 crop transfer factors |
| F07 | funding_registry | UNFPA Flash Appeal for Lebanon (Mar-Aug 2026) | UNFPA | as published | 2026-11-21 | Funding registry F007; M5 cost lines |
| D09 | funding_flows | LHF / CBPF project summary (Lebanon fund 71) | OCHA CBPF / HDX | CC BY | 2026-11-21 | governance baseline (national NGO share of LHF) |
| D10 | vulnerability | VASyR 2025 and MSNA 2025 (UNHCR/WFP/UNICEF; REACH/UN Women) | UNHCR / UN Women | not stated | 2026-11-21 | M2 vulnerability |
| D11 | facilities | WHO EMRO Lebanon sitreps #24-30 and UNICEF SitRep 5 | WHO / UNICEF | as published | 2026-11-21 | facility status |
| D12 | conflict_exposure | UCDP GED Lebanon and HDX ACLED admin-2 monthly | UCDP / ACLED via HDX | CC BY-IGO (UCDP); ACLED terms (do not redistribute) | 2026-11-21 | S1 escalation scenario |
| D13 | governance_capacity | UN-Habitat Lebanon Rapid Municipal Assessment 2026; Citizen Budget 2026; WB WGI; IMF TA report | UN-Habitat / MoF / WB / IMF | as published | 2026-11-21 | state capacity |
| D14 | haus_2024 | UNHCR HAUS 2024 report (supplied by the team) | UNHCR Lebanon | not stated | 2026-11-21 | appendix; cascade sources |

Added after the manifest (each has a `_provenance.json` or a README in `data/raw/`): MoPH facility list and PHC network (2026-11-21), costs pack, Beqaa funding and partners, WorldPop age/sex, damage figures, projects inventory, surveillance (MoPH ESU to 7 Aug 2026, WHO briefs, WBD risk map), care-flow pack, evidence and price packs, AUB lab prices.
ACLED is not used (the account returned HTTP 403 on OAuth and its tier gives only events older than 12 months); ACLED data are never committed.
