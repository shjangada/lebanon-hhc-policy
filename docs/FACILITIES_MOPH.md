# Facility base: MoPH list replaces OSM

Source: `data/raw/facilities/moph_bekaa/` (MoPH Health Facility Locator + MoPH PHC network list dated 27/03/2025, retrieved 2026-11-21; see `_provenance.json`). Ingest: `src/beqaa/ingest/facilities.py` (`build_facilities_moph`). OSM is used only if the MoPH file is absent.

| | OSM base (before) | MoPH base (now) |
|---|---|---|
| PHCs in the five districts | 41 clinics/hospitals tagged, about 15% of the 61 network PHCs | 65 PHCCs (59 network + 6 locator-only; 3 network centres have no village coordinate and are listed in `_unmatched.csv`) |
| Hospitals | in OSM | 29 (6 public, 23 private) |
| PHC location | OSM point | village centroid from the MoPH address (`coord_confidence=village`, 1-5 km) |
| Dated 2026 status | 2 hospitals | 4 facilities (WHO sitreps, MSF); all PHCCs unknown, counted at the dashboard's "unknown" setting |

## Effect on access (E2SFCA, d0 = 30 min, women 15-49, median by district)
| District | pre-war OSM | pre-war MoPH |
|---|---|---|
| Baalbek | 0.119 | 0.170 |
| Hermel | 0.111 | 0.123 |
| Rachaya | 0.293 | 0.613 |
| West Bekaa | 0.298 | 0.362 |
| Zahle | 0.381 | 0.360 |

Cadasters with zero access: 12 of 222 (OSM) to 3 of 222 (MoPH). Rank correlation of the access ranking with the official health severity (HDX/LRP): rho 0.29 (OSM) to 0.58 (MoPH).

## Not solved
Capacity and ANC offering are still assumptions; PHCC positions are approximate; the list is March 2025 and misses about 3 network centres; names were read through web extraction and must be checked against the PDF (`docs/MANUAL_STEPS.md`). Road travel times (OSMnx) are not yet used: travel time is still straight line x 1.3 at 40 km/h.

## Capacity (assumption, now tested)
- **Hospitals:** weekly capacity = 2000 x (MoPH medicine-ward beds / median beds); 12 of 29 hospitals have a bed count (medicine department only, not all beds), the rest keep 2000. Range 800 to 5,333.
- **Centres:** no size data exists (no staff, hours or volumes), so every centre stays 300 consultations/week and M1 is run at **200 / 300 / 400** (`m1_access.capacity_sensitivity`). Median current access by district moves with the level (Baalbek 0.146 / 0.170 / 0.195; Zahle 0.317 / 0.347 / 0.382) but the **ranking of cadasters does not** (Spearman 0.997 between 200 and 400). So the access ranking is robust to centre size; access levels are not.
- Real staffing per centre needs the MoPH PHC department (docs/DATA_REQUESTS.md).
