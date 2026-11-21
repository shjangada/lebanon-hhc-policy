# LRP 2026 Addendum (Sep-Dec 2026): district severity transcription

Source: `Lebanon Response Plan 2026 - Addendum Sep-Dec 2026.pdf` (70 pages). Hand-transcribed from rendered page images (labels printed under each district name on the choropleths; colour checked against legend). Values are severity CLASSES (1-5) only; no numbers were invented.

## What exists (and where)
| Page | Content | Indicator in CSV |
|---|---|---|
| 11 | Inter-Sectoral Severity map (JIAF 2.0), 26 districts, with population-figure bubbles (bubbles are size classes only, not transcribed) | `jiaf_severity` |
| 12 | Education Severity; Food Security Severity | `sector_severity_education`, `sector_severity_food_security` |
| 13 | Health Severity; Nutrition Severity | `health_severity`, `sector_severity_nutrition` |
| 14 | Livelihoods Severity; Protection Severity (incl. CP and GBV) | `sector_severity_livelihoods`, `sector_severity_protection` |
| 15 | Shelter Severity; Social Stability Severity | `sector_severity_shelter`, `sector_severity_social_stability` |
| 16 | WASH Severity | `sector_severity_wash` |
| 3 | At a Glance + Planning Figures table: NATIONAL People in Need (total, humanitarian/stabilization split, per sector) | `pin_*` (admin_level = national) |
| 22-23 | Food Security sector narrative: composite conflict-impact food-security index; text lists Severity-4 districts | `fsa_composite_severity` |

All 26 districts are covered in each map. Governorate column follows the document's own groupings (Bent Jbeil, Marjaayoun, Hasbaya, El Nabatieh in Nabatieh; Jbeil in Mount Lebanon; Akkar as its own governorate).

## What was NOT shown
- No FSA composite conflict-impact severity MAP or table. Only the text on pp. 22-23 states that Severity 4 districts are Baalbek, El Hermel, Bint Jbeil, El Nabatieh, Marjaayoun, Sour, Aley, Baabda. Those 8 get value 4; the other 18 districts have an empty value with note "missing". (The p. 12 Food Security Severity map is a different product and is recorded separately as `sector_severity_food_security`.)
- No People in Need by district or governorate anywhere. Only national PiN (p. 3); sector PiN values there are rounded as printed (e.g. "327 K", "1.2 M"), and Logistics/Telecom and MPCA have no PiN ("-"/blank, not recorded).
- No population-group split of the severity maps. The p. 4 Conflict Intensity Snapshot is a map of incidents, not a severity class, and was not transcribed.
- No severity map for Logistics/Telecom, Child Protection or GBV separately (Protection map includes CP and GBV).
- Text on p. 36 mentions a livelihoods proxy model with nine Severity 3 districts; it is consistent with, and not additionally recorded from, the livelihoods map.

## Method / QA
Pass 1 from 110-dpi page renders, pass 2 from 230-dpi crops, independent re-reading; diffed with Python. Result: 300 rows, 0 disagreements, so all rows checked=True. Caveat: both passes were by the same transcriber in the same session, so pass 2 is not blind in the strict sense; small labels outside polygons (Beirut, Tripoli, Saida) were cross-checked against polygon colour. Intermediate files: `lrp_addendum_severity_pass1.csv`, `lrp_addendum_severity_pass2.csv`.

## Beqaa districts
West Bekaa, Zahle, Rachaya (Bekaa) and Baalbek, El Hermel (Baalbek-Hermel) have JIAF, Health and all nine other sector severities. FSA composite = 4 only for Baalbek and El Hermel; West Bekaa, Zahle, Rachaya are not listed (missing).
