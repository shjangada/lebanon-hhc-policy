# Surveillance & water-risk data: Beqaa Valley (Bekaa + Baalbek-Hermel)

Retrieved 2026-11-21. Sources and URLs are in `_provenance.json`.

## Files
| File | Content |
|---|---|
| `esu_by_month.csv` | MoPH ESU reported cases by month (year, mohafaza_file, disease_group, disease, month, cases, as_on, source_url). Covers all 32 notifiable diseases. Includes Bekaa 2019-2026, Lebanon national 2023-2026, and Baalbeck and Hermel caza files for 2026. `month=TOTAL` is the published total. |
| `esu_by_age_sex.csv` | Same files, by age group (0-4 to 60+, unknown) and sex (group_type age/sex/total). |
| `esu_by_district.csv` | By place. For Bekaa files these are cazas (Hermel, Baalbeck, Zahleh, West-Bekaa, Rashaya, Unknown). For Lebanon files these are the old 6 mohafazat (Beqaa = Bekaa + Baalbek-Hermel combined). The caza files have no place table. |
| `who_health_briefs_wbd.csv` | WHO Lebanon Health Briefs, Apr 2025 to May 2026: national new AWD cases, cholera lab-confirmed, hepatitis A new suspected/confirmed/cumulative, and hepatitis A by governorate (8 governorates, incl. Bekaa and Baalbek/Hermel separately). |
| `wbd_risk_map.csv`, `wbd_risk_map_method_notes.md` | WaSH Sector WBD risk map: 2024 top-20 cadasters (11 in the Beqaa Valley) and 2025 national High/Medium/Low cadaster counts. Includes the methodology and the reasons no district classes were recorded. |
| `raw/esu_compact.txt` | Hash-verified compact transcript of all ESU tables (H = header row, Z = all-zero row). |

## Coverage
- ESU **2026 runs only to August**, with tables "as on 07/08/2026". August is partial and Sep-Nov 2026 was not yet published at retrieval. Even after year end, the last months stay incomplete: 2025 Nov and Dec are 0 and Oct is very low ("as on 02/01/2026"), which is reporting lag, not true zeros.
- The ESU "Bekaa" file uses the **old Beqaa mohafaza** (it includes the Hermel and Baalbeck cazas). There is no separate Baalbek-Hermel mohafaza file, and Baalbek.htm / BaalbekHermel.htm return 404. Caza files Baalbeck.htm and Hermel.htm exist for the current year only.
- WHO briefs: hepatitis A governorate counts are per brief period, not cumulative. The briefs do not say whether they are suspected or confirmed, but they roughly equal new suspected + confirmed. Periods have uneven lengths (2 to 6 weeks) and some have gaps.

## Caveats
- ESU numbers are **reported (notified) cases**: suspected and confirmed mixed, with no population denominator. Expect **under-reporting**, which varies with health-seeking behaviour, lab access and reporting by facilities (including UNHCR/NGO clinics serving refugees).
- Cases are assigned **by place of report or residence as notified**, not necessarily where infection happened. Cases among displaced people may be attributed to the host caza.
- Past-year files were revised later (as-on dates up to 03/10/2025 for 2020-2023), so figures can differ from earlier publications.
- **Cholera** in the ESU tables shows 114 Bekaa cases in 2023 (Jan-Feb) and 0 in 2022, although the outbreak began in Oct 2022. The 2022-23 cholera outbreak was tracked mainly through a separate MoPH cholera dashboard, so do not use the ESU tables alone for cholera.
- Source inconsistency: in the 2022 Bekaa by-place table, Meningitis TOTAL is 68 but the cazas sum to 67. Both were kept as published.
- WHO brief values come from PDF text extraction. Their labels depend on layout, and the attribution of the "new suspected/confirmed/cumulative" line to hepatitis A is inferred (cholera confirmed = 0, and the cumulative figures match the ESU national hepatitis A total). The Sep-Oct 2025 brief's section header repeats "10 Aug-10 Sept". The 26 Jul-9 Aug 2025 file duplicates the 26 Jun-9 Aug content.
- The 2025 risk map publishes no weights, thresholds or cadaster list. The map image cannot be read at district level, so those cells are left blank on purpose.
