# Manual download checklist (put files in `data/raw/`)

Most sources need a browser or login. Files must match the columns in CLAUDE.md section 4. Delete a file to fall back to mock.

- [ ] `cadasters.csv` + `admin_boundaries/` — HDX COD-AB Lebanon (admin 1–3)
- [ ] `population.csv` — WorldPop age/sex 100 m; IOM DTM latest round; UNHCR registration by cadaster; unregistered workers = **assumption** (document method)
- [ ] `facilities.csv` — MoPH Health Facility Locator; HDX "Lebanon PHCs"; UNHCR PHC list 2018; WHO sitreps; Health Sector dashboards
- [ ] `travel_time.csv` — OSM via osmnx, or Malaria Atlas Project travel-time raster
- [ ] `vulnerability.csv` — IPC Lebanon (Dec 2025 / Apr 2026); VASyR 2025; REACH MSNA 2025; LRP 2026 Addendum
- [ ] `official_severity.csv` — LRP 2026 Addendum JIAF 2.0 maps; FSA composite index
- [ ] `soil_sites.csv` — CNRS-L/MoE Apr 2026 Ch. II + Table 2.3 (BE sample IDs)
- [ ] `water_quality.csv` — Litani River Authority; Darwish et al. 2011; 2025–26 monitoring
- [ ] `crop_transfer.csv` — Abi Saab et al. 2022 (Water 14:1437)
- [ ] `interventions.csv` — UNFPA & WHO appeal lines; K2P/UNICEF PHC financing memo (Oct 2025); implementer quotes
- [ ] `cascade_baseline.csv` — Benage 2015; Tappis 2017; Conflict & Health 2023; VASyR 2025; referral completion = assumption
