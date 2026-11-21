# Data: what we have, how we use it, why

Everything real lives in `data/raw/`; everything synthetic lives in `data/mock/` and is flagged `is_mock`. The dashboard uses a real file instead of a mock one **only when it exists under the schema name** in `data/raw/` (e.g. `data/raw/population.csv`, see `src/beqaa/io.py`). The downloads below are the *raw sources*. Converting them into those schema files is the next step, so the app still reports **MOCK** today.

## From raw downloads to model inputs
`python -m beqaa.ingest all` (or `make ingest`; one script per dataset in `scripts/ingest/`) converts the raw downloads and the hand transcriptions in `transcribed/` into the project's dataset schemas in **`data/processed/`**. Every processed row carries `is_mock=False`, `source_id`, `source_date`, `url`, `status`. `io.load_dataset` prefers processed files and falls back to `data/mock/`; `io.validate_consistency()` stops the pipeline if cadaster-keyed datasets mix real and mock ids. Names are matched through COD-AB p-codes (`name_crosswalk.csv`); anything that fails to match is listed in `_unmatched.csv`, never dropped silently. Nothing missing is filled with an invented value: it stays empty with `status=missing`.

Real now: cadasters (222 admin-3 areas), population by group (LRP + WorldPop + DTM; Syrian registered/unregistered split is an assumption), conflict incidents (LRP), IPC (district), FTS funding flows, LHF partner shares, official severity (hand-transcribed LRP Addendum classes), soil (5 villages located by name), crop transfer factors (Abi Saab), facilities (OSM, 15% of MoPH PHCs; 2 hospitals with a dated status), travel times (modelled; cross-checked against HDX accessibility). Still mock or partial: interventions, cascade, water quality, staffing, governance capacity, household indicators. See `docs/DATA_STATUS.md`.

**Hand transcriptions** (`transcribed/*.csv`) follow two passes (`*_pass1.csv`, `*_pass2.csv`) with `page`, `table_or_figure`, `transcribed_by` and `checked`. Both passes of one agent are less independent than two people: read `checked=True` as "no typo found", not "verified by a second person".

**ACLED terms:** raw ACLED files and ACLED-derived counts are gitignored (no redistribution).

## Keeping it up to date
```
python scripts/fetch_sources.py            # download anything in data/registry/data_manifest.csv that is missing
python scripts/fetch_sources.py --check    # compare HDX last_modified with the local copy (STALE / ok)
python scripts/fetch_sources.py --refresh  # re-download everything
```
`data/registry/data_manifest.csv` is the single list of sources (id, dataset it feeds, URL or HDX package, licence, why, refresh cadence, status). Each downloaded folder also gets a `_provenance.json` (URL, retrieval date, SHA-256). Files over 5 MB are not committed (admin-boundary GeoJSON, soil report PDF); the script re-downloads them. Downloaded files are untrusted data: the script only saves them. Inspect with `python -I`.

## Downloaded (real data)
| Folder (`data/raw/…`) | Source | What is in it (checked) | Feeds | Why we use it | Refresh |
|---|---|---|---|---|---|
| `admin_boundaries/` (D01) | OCHA COD-AB via HDX | Admin 0–3 polygons (GeoJSON zip, not committed) and name/p-code tables (xlsx). Admin 3 is the cadaster level | cadasters (all models) | Replaces the synthetic cadasters with real names, p-codes and geometry | yearly |
| `facilities/hotosm_osm/` (D02) | HOT / OSM via HDX, 2026-11-15 | 1,392 health features: 1,036 pharmacies, 201 hospitals, 66 clinics, 33 doctors, 30 dentists, 8 labs, with coordinates; data-quality report | facilities (M1 access, M2 capacity) | Current facility coordinates. **No open/closed status or capacity**: those still come from the WHO sitrep map and partners | monthly |
| `facilities/who_sitrep_23/` (S03) | WHO EMRO sitrep #23 (PDF) | Map of closed facilities by type (May 2026) | M1 closure scenario | Only closure map found; closed facilities must be transcribed by hand | per sitrep |
| `population/lrp_2026/` (D03) | GoL/UN LRP 2026 population package (xlsx) | Sheets: summary by governorate for 2025 and 2026 planning figures (Lebanese, Palestinians, Syrians, migrants), age/sex tables per group, conflict incidents for 410 admin-3 areas, IDP origin–destination and returns, PHC counts per district (MoPH network), SDC and school counts | population (M1 demand, M2 clinical demand, equity groups) | Official population by group. Example from the file: Syrians are 192,072 of 417,109 (46%) in Baalbek-El Hermel in the 2025 column. Conflict incidents give a damage/stress layer | yearly |
| `population/iom_dtm/` (D04) | IOM DTM via HDX | 10,492 rows, admin 0–2, IDPs present by reporting round | population (displaced) | Current displaced counts by district | monthly |
| `population/worldpop/` (D08) | WorldPop age/sex 2025 (1 km) | GeoTIFF zip, all age/sex bands | M1 women 15–49 share | Cadaster-level share of women 15–49 (100 m rasters, 210 MB each, deliberately skipped) | yearly |
| `vulnerability/ipc/` (D05) | IPC via HDX, analysis Sep 2026 | 42 area rows: population analysed, phase 3+ number and share by area; GeoJSON of areas | vulnerability (M2 `ipc3plus_share`) | District/area food-insecurity severity | per IPC round |
| `funding_flows/fts/` (D06) | OCHA FTS via HDX | Requirements/funding by year (55 rows) and cluster; 956 incoming funding flows with source and recipient organisation types | funding finder, dependency metric (money by recipient type) | Replaces the mock funding-flow chart with real flows | weekly |
| `travel_time/accessibility/` (D07) | HDX accessibility indicators | PHC and hospital access by admin level and travel-time range (population covered) | M1 cross-check | Independent check on our E2SFCA access and travel-time assumptions | yearly |
| `soil_sites/cnrs_2026/` (S27) | CNRS-L/MoE report (PDF, not committed) | Ch. II soil results; Beqaa sites in Table 2.3 | M4 exposure, M2 environment | Only Beqaa soil data. Values are already in the mock `soil_sites.csv`; **site locations still need real coordinates** | one-off |
| `funding_registry/unfpa_flash_appeal/` (F07) | UNFPA Flash Appeal Mar–Aug 2026 (PDF) | Maternal/SRH appeal lines | registry row F007, M5 cost lines | Fills the missing amount for F007 and gives real cost lines | one-off |
| `worldbank_population/` | World Bank WDI | National total population by country, 1960–2025 | Story context, national sanity check | National only; cannot replace cadaster population | yearly |

## Not downloaded
| Source | Why | What to do |
|---|---|---|
| S28 Abi Saab et al. 2022 | MDPI blocks automated download (403) | Save the PDF into `data/raw/crop_transfer/abi_saab_2022/`, transcribe transfer factors |
| S08 MoPH population by age/nationality | Catalog URL returns 404 | Superseded by the LRP package (D03) |
| S01, S02 (Health Sector sitrep #24, At a Glance), S07, S12, S17, S18 | PDFs/dashboards on data.unhcr.org and unocha.org (JS portals) | Download in a browser, add a manifest row with the file URL |
| S04 MoPH facility locator | Website with no coordinates | Scrape later and geocode by town, or rely on D02 |
| S10 UNHCR active Syrian records | Dashboard, no file | Export from the portal; gap to LRP planning figure is the unregistered-worker proxy |
| S14 VASyR 2026, S16 UNFPA sitrep, S20 VOICE, S23 UN-Habitat | PDFs/portals not fetched; not needed until the model uses them | Add when needed |
| S15 LRP Addendum severity (JIAF/FSA) | Severity maps are images | Transcribe district values into `official_severity.csv` |
| S24–S26 evidence papers, S29 ACAPS, S30 OSM roads | Evidence, not data (or very large) | Cite; roads (OSM) only if we compute travel times ourselves |

## Mock datasets and what replaces them
| Mock file | Real source now available | Still missing |
|---|---|---|
| cadasters | D01 admin 3 | converter |
| population | D03 + D04 + D08 | converter; **unregistered workers remain an assumption** (gap between LRP Syrian estimate and UNHCR records) |
| facilities | D02 coordinates | open/closed status and capacity (S03 + partners); ANC offering |
| travel_time | compute from OSM roads, or use D07 as a cross-check | decision on method |
| vulnerability | D05 (area level) | cadaster-level indicators other than IPC (VASyR, MSNA) |
| funding_flows | D06 | converter |
| official_severity | S15 (images) | transcription |
| soil_sites | S27 values | real site coordinates |
| crop_transfer | S28 | manual download and transcription |
| interventions, cascade_baseline, water_quality | none public found | partner quotes, literature (cascade), monitoring data |
| governance_capacity, staffing_referrals | none public; likely only via MoPH / NGO partners | **these are the least obtainable mocks**: treat as pilot indicators, not baseline data |
