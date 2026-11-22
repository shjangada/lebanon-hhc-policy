# care_flow: primary care, outreach, referral and WASH in Bekaa / Baalbek-Hermel (as of 2026-11-21)

All values come from the cited URLs, accessed 2026-11-21. Nothing has been imputed. "NOT FOUND" marks a gap.

## Files
- `informal_settlements.csv`: IS counts by district (IAMP34, Dec 2016, the latest public site-level list), plus newer proxies (IAMP Bekaa March 2018; WaSH 2026 ITS reach; VASyR 2025).
- `informal_settlements_by_cadaster_2016.csv`: 134 cadasters in Zahle, West Bekaa, Baalbek, Hermel and Rachaya. Includes active and "less than 4 tents" sites, tents, individuals, mean lat/lon, and the number of sites using trucked water. I computed it in-browser from the HDX xlsx (sheet "IAMP34 All sites", 6,271 sites with coordinates). The raw file is too large to relay. Download it from https://data.humdata.org/dataset/informal-settlements-refugees-living-in-informal-settlements
- `outreach_services.csv`: MSF, Amel, MoPH/WHO PSUs and outreach units, UNICEF PSUs, LRC.
- `referral_payers.csv`: who pays for what, for Lebanese, registered Syrians and unregistered Syrians.
- `wash_activities.csv`: ITS trucking, desludging, water-quality and quantity findings.
- `capacity_waittime.csv`: PHCC counts, volumes, access percentages.
- `water_sampling_guideline.md`: WHO GDWQ Table 4.4 and the worked cadence.

## What exists today (key points)
1. **Hospital care for Syrians collapsed.** UNHCR hospitalization support ended on 1 Dec 2025, and IOM also stopped by end-2025 (per MSF). A funds-dependent "support program" at contracted government hospitals lists 100% cover for life/limb cases, a $170 / $300 patient share for deliveries, and 60% for NICU. Its operator is not named. Non-Lebanese war trauma goes to the WHO/ECHO life- and limb-saving project.
2. **Lebanese:** MoPH covers 100% at government hospitals for uninsured Lebanese during the war (normally 80%). The 1787 hotline handles referral to hospitalization.
3. **PHC:** the MoPH network has 28 PHCCs in Baalbek-Hermel and 37 in Bekaa (2025) and is open to all nationalities. The LPSP fee is $2 (GP) or $3.5 (specialist) at subsidized centres. For refugees at partner PHCCs, consultations cost LBP 150k–900k, while vaccines and acute medicines are free.
4. **Outreach to camps:** MSF runs a Hermel centre with a mobile clinic, a clinic in Arsal, and mobile teams across Bekaa. Amel has 14 MMUs covering 65 sites, including informal settlements. **No visit frequency is published by any actor.**
5. **WASH:** 112,629 people in ITS were reached with WaSH nationally (Jan–Sep 2026). Water delivered was 15–20 L/p/d against a 35 L standard (2024), and 72% of tested water samples in Baalbek-Hermel ITS were faecally contaminated (July 2026).

## Gaps
- No public **current** IS site list. IAMP data after 2018 is on partner-restricted platforms. Ask the Inter-Agency IM unit or the WaSH sector for the current IAMP extract.
- No district-level breakdown of the health 4W/MMU data. The Health Sector mid-year 2026 dashboard PDF (14 MB) and HAUS 2024 could not be parsed by my tools, so download and check them manually: https://data.unhcr.org/en/documents/details/124193 and https://data.unhcr.org/en/documents/details/115759
- Visit frequency for MMUs, UNHCR outreach volunteers, IMC, UNFPA: not found.
- Payer for non-trauma hospital care for **unregistered** Syrians: not found.
- PHCC waiting times and referral completion for Bekaa / Baalbek-Hermel: not found.
- FRC/chlorination testing cadence and % of IS below 15 L/p/d: not found.
- The WASH EOY 2025 dashboard (https://data.unhcr.org/en/documents/details/122055) could not be parsed.
