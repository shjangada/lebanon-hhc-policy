# MoPH health facilities: Bekaa and Baalbek-Hermel

Retrieved 2026-11-21. One row per facility. Sources and method are in `_provenance.json`.

## Coverage (rows by caza and type)

| caza | PHCC (of which in 2025 network) | hospital_public | hospital_private | total | facility coords | village coords |
|---|---|---|---|---|---|---|
| Zahle | 23 (21) | 1 | 9 | 33 | 9 | 32 |
| West Bekaa | 11 (11) | 2 | 3 | 16 | 4 | 16 |
| Rachaya | 5 (4) | 1 | 1 | 7 | 1 | 6 |
| Baalbek | 25 (23) | 1 | 7 | 33 | 5 | 32 |
| Hermel | 4 (3) | 1 | 3 | 8 | 2 | 8 |
| **Total** | 68 (62) | 6 | 23 | 97 | 21 | 94 |

## Key columns
- `moph_network`: `yes` = in the MoPH PHC-network list dated 27/03/2025 (62 centres). `no` = PHC centre listed only in the MoPH online locator (6), or a hospital (hospitals are not network centres by definition).
- `lat`/`lon`: **facility-level** coordinates only, from OSM name matches (hospitals only). `coord_confidence` is high or medium. No PHC centre matched in OSM, so PHC `lat`/`lon` are blank.
- `village_lat`/`village_lon`: OSM centroid of the village in the MoPH address. Use this only as a rough location (accurate to about 1 to 5 km); it is not the facility's own position.
- `moph_registry_status`: the 'Status' field on MoPH locator detail pages ('open'). This is an old registry field, **not** the facility's 2026 operating status.
- `functional_status`: from dated 2026 sources only; `unknown` when no source names the facility.

## Status findings (2026)
- West Bekaa Hospital (Sohmor), named as 'Bekaa Gharbi Hospital': partially damaged (WHO sitrep #21, 24 Apr 2026; still listed in #23, 8 May 2026).
- Baalbek Governmental Hospital: functional and MSF-supported, with a paediatric ICU being set up (MSF, 18 Aug 2026).
- Libano-Francais Hospital (Zahle): functional, with an MSF maternity partnership (MSF, 18 Aug 2026).
- The other 94 rows are `unknown`. WHO and Health Sector sitreps give only national counts of closed PHCCs (43 to 59 between March and May 2026) and do not name the centres or say where they are.

## Gaps and caveats
- **Dispensaries**: none found in any MoPH source for these cazas, so the file has none.
- **Missing network centres**: the MoPH 2025 Annual PHC Dashboard counts 37 Bekaa and 28 Baalbek-Hermel network centres. The March-2025 list used here has 36 and 26, so about 3 newer centres are missing. No newer list could be retrieved: the PDF URL returned 404 on 2026-11-21.
- **How the network list was read**: the network PDF could not be downloaded. Its text was taken through two independent web-fetch extractions, which agreed with each other. Check names and phone numbers against the PDF before publishing.
- **No English names for 30 network centres**: these centres are not in the online locator, so `name_en` is blank (no translation was invented).
- **Private hospitals may be incomplete**: the MoPH locator lists 23 private hospitals in these cazas. Hospitals registered elsewhere, or newer ones, may be missing.
- **Inconsistent cazas**: one MoPH row lists Iben Sinna Hospital under caza Hermel, but its address is Baalbek. It is kept as Hermel, as MoPH gives it.
- **Villages not geocoded**: الفاعور, عزة, الفاكهة.
- **Facility IDs** follow the pattern `<CAZA>-<TYPE>-<nn>`. They are local to this file and are not MoPH codes; `moph_locator_id` holds the MoPH locator ID where one exists.
