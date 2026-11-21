# Manual steps and blocked items

Items the ingest could not finish without a person. Each says what to do and where the result goes. Nothing here has been filled with an invented value.

## 1. ACLED (event-level conflict data): needs you
`src/beqaa/ingest/acled.py` is written and tested (no credentials are ever printed, logged, cached to disk or committed). On the last run the token request returned **HTTP 403**, so the script stopped without retrying (as instructed).
1. Check your login at <https://acleddata.com> and whether your account tier allows **API access** (myACLED accounts need it enabled; the 403 means the credentials or the tier were refused).
2. Make sure `.env` (gitignored) contains `ACLED_EMAIL=` and `ACLED_PASSWORD=` (see `.env.example`).
3. Run `python -m beqaa.ingest acled`. It writes `data/raw/conflict_events/acled/` and `data/processed/conflict_events.csv` (events and fatalities in the last 30/90/365 days per cadaster, and `access_degraded`; rule in `data/params/conflict_access.yaml`). Both are **gitignored**: ACLED's terms forbid redistributing raw data, and the output must carry the ACLED attribution.
Until then: the public HDX ACLED file gives **district-level, monthly** counts only (`data/processed/conflict_events_district_fallback.csv`, gitignored); UCDP event data stops at 2024-12 (`data/raw/conflict_events/hdx/`).

## 2. Data with no public source (stay scenario inputs, flagged as assumptions)
| Data | Why it is missing | Route |
|---|---|---|
| Well / river nitrate | no public dataset | data request to the Litani River Authority (and the MoE/CNRS-L soil team for locations) |
| Intervention unit costs | the UNFPA appeal has no unit costs | quotes: AUB lab (Cr(VI) speciation), UNFPA/WHO (mobile unit), CHW stipends from IRC/UNFPA |
| Health-worker top-up amounts | no public figure (IMF report W19 has minimum wages only) | MoPH PHC department / NGO partners |
| Staffing, referral completion | not published | MoPH PHC department, NGO records; pilot indicator |
| Bekaa doctor / nurse counts | not found | Order of Physicians, MoPH |
| District governance capacity | the UN-Habitat RMA publishes only aggregates for a national sample of 38 municipalities (`docs/ADMIN_CAPACITY_INDEX.md`) | request the municipality-level RMA data from UN-Habitat Lebanon |
| Community priority weights | only a pilot survey can produce them | participatory exercise |
| Referral completion in the cascade | no source found | pilot-collected |

## 3. Data that exists but is not machine-readable or not found
- **Facility functionality at facility level for PHCs:** WHO sitreps give national totals only (41 PHCCs closed in #23; 24 on 3 Aug); hospital names are given without locations (2 matched by name). HeRAMS is not on HDX. Ask the Health Sector (data.unhcr.org/en/working-group/19) for the facility list.
- **MoPH facility locator** (S04): the JS-driven filters could not be driven by a simple request; it would give the full PHC list (61 in the five districts). Scrape in a browser or ask MoPH.
- **VASyR / MSNA at district level:** only governorate-level 'below SMEB' exists for Syrian households; female-headed households, ANC, care barriers and insurance are national only. Ask UNHCR/REACH for the microdata (microdata.unhcr.org; REACH Resource Centre).
- **Mobile unit routes / hours:** none published (MSF, UNFPA, SAMS name places only). Ask the operators; capacity = hours per week / 40 needs hours.
- **Soil coordinates and sample-level values:** the CNRS-L report lists BE sample IDs but no coordinates and no ID-to-value link. Ask CNRS-L/MoE for Table 2.3 with coordinates.
- **Roads (HDX `hotosm_lbn_roads`)** for our own travel times: **not done.** Travel times are straight-line x 1.3 / 40 km/h (assumption); the HDX accessibility file agrees at district level (Spearman 0.90 on the share within 30 minutes of a PHC), but district-level agreement is weak evidence for cadaster-level times.
- **Pb / As crop transfer:** Abi Saab et al. 2022 covers Cr, Ni, Zn, Cu, Cd only.

## Verify by hand: MoPH facility list
The PHC network list was read through web extraction (the PDF could not be downloaded). Check `name_en`/`name_ar`/phones in `data/raw/facilities/moph_bekaa/moph_facilities_bekaa.csv` against <https://moph.gov.lb/userfiles/files/HealthCareSystem/PHC/phcc.pdf> (404 on 2026-11-21; ask MoPH for the current list). About 3 newer network centres are missing; 3 PHCCs have no village coordinate.

## ACLED outcome (2026-11-21)
The OAuth token request now sends the documented `scope=authenticated` and still returns HTTP 403 (stopped, not retried in a loop). A browser call with the account's cookie session did return data, and its `data_query_restrictions` show `date_recency: 12 months` (events up to 2025-11-21 only, restricted countries/regions list empty). So this account tier gives **no 2026 events**: the planned "last 30/90/365 days" access flag cannot be built from it even if OAuth worked. Options: (a) keep the LRP incident counts (to Jul 2025) as the conflict layer; (b) ask ACLED for a research tier with current data; (c) use the HDX ACLED district-month file (district level, as of 18 Nov 2026) for a fallback. Do not commit ACLED data.
