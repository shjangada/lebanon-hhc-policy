# Waterborne Disease (WBD) Risk Map - method notes

Retrieved 2026-11-21. Two Lebanon WaSH Sector documents hosted on the UNHCR Operational Data Portal.

## A. "Update of water-borne diseases (WBD) risk map as a warning for new threats in Lebanon" (2024)
- URL: https://data.unhcr.org/ar/documents/download/109156 (about 6 pages). Authors: M. Wehbi, J. Pajak, H. Younes (Lebanon WaSH Sector).
- Unit: cadaster (admin 3). Score = weighted sum of 10 indicators, **each weight 0.1** (max score 1; higher means more risk).
- Indicators and sources:
  1. Population density, incl. displaced Syrians, informal settlements (IS), IDPs (Inter-Agency population package)
  2. WBD cases, past and current year (MoPH ESU)
  3. Self-reported water-related illness in IS (WaSH Assessment Platform)
  4. Water samples failing LIBNOR standards (MoPH ESU water quality)
  5. Functional public water supply infrastructure (NWSS; WatSan Infrastructure Assessment)
  6. IS below 15 litres/person/day (WaSH partners 3W, May 2024)
  7. Sanitation access and WWTP functionality (NWSS; WatSan Infrastructure Assessment)
  8. Desludging services in IS (3W, May 2024)
  9. Proximity to permanent or seasonal rivers (NWSS)
  10. Flood risk from 2017-2024 flood records (WaSH Assessment Platform)
- The text gives no class thresholds. It publishes only a **top-20 highest-risk cadasters** list (p.5), and 11 of the 20 are in the Beqaa Valley: Barr Elias (4), Saadnayel (5), Aali En-Nahri (8), Taalbaya (15), Ablah (20) in Zahle; Aarsal (6), Taraiya (7), Haouch Er-Rafqa (9), Khodr (18), Bednayel (19) in Baalbek; Kamed El-Laouz (13) in West Bekaa. No Hermel or Rachaya cadasters are in the top 20. The document points to a full list and map, but neither is included and no link is given.

## B. "Early Warning: 2025 Waterborne Disease Risk Map, Lebanon" (WaSH Sector; published 15 Aug 2025, uploaded 5 Sep 2025)
- URL: https://data.unhcr.org/en/documents/download/118462 (7 pages, no printed page numbers). Authors: Mahdi Wehbi (WaSH Sector IMO, UNICEF), Jakub Pajak (WaSH Sector Coordinator, UNICEF), Hussein Younes (Co-coordinator, World Vision).
- Builds on the 2022 Cholera Risk Map and extends it to all WBD. Indicators are normalised in GIS into a cadaster risk score:
  - population density and vulnerability (incl. collective shelters, IS, share of under-5s and elderly)
  - proximity to contamination sources (rivers, polluted sites)
  - access to functional water infrastructure (hostilities damage and drought impacts, 2024-25)
  - recent WBD occurrence (MoPH ESU cases for current and past year, weighted to the last 6 months, plus IS self-reported symptoms)
  - non-conforming water samples (% failing LIBNOR, weighted to recent results)
  - **Drought Vulnerability Index (DVI 2025)**: precipitation anomaly, hydrogeological resilience, groundwater quality, land use/cover, population pressure
  - sanitation and wastewater (access, WWTP functionality 2024, desludging coverage in IS)
- **Weights and thresholds are not published.** There are three classes, High, Medium and Low, shown in the chart "Cadasters by WBD category: annual trends". Number of cadasters in each class (out of 1,610):

  | Date | High | Medium | Low |
  |---|---|---|---|
  | Sep 2022 | 147 | 317 | 1146 |
  | Sep 2023 | 79 | 274 | 1257 |
  | Sep 2024 | 81 | 280 | 1249 |
  | 2025 ("Today") | 85 | 371 | 1154 |

  The chart marks these events: water alert (2022), hostilities and some IDPs (2023/24), escalation and mass displacement (late 2024), drought (2025). Its "Expectation" arrows point up for High and down for Medium, without values. The text says **85 highly vulnerable cadastres** nationally.
- **Map**: a cadaster choropleth in a continuous colour ramp (light yellow to dark red). Cadasters are not labelled and the legend is truncated (only "0" is visible), so **no district or cadaster class can be read reliably and none was recorded**. A qualitative reading only, not data: dark-red (high) clusters run along the central Bekaa plain, roughly the Zahle and West Bekaa corridor along the Litani, and around the Baalbek plain. There is also a large dark-red polygon on the north-eastern border, consistent in location with Aarsal. The northern Hermel area looks mostly light to orange, and the Rachaya highlands mostly light. To get exact classes, ask the WaSH Sector IMO for the cadaster list or shapefile.
- **Caveat**: the two documents use different indicator sets. The 2025 document does not publish a cadaster list, so the 2024 top-20 ranks must not be presented as 2025 classes.
