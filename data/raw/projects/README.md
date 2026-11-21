# Bekaa / Baalbek-Hermel funded projects inventory (health attachability)

Compiled 2026-11-21. Desk search took about 45 minutes, using WebSearch and WebFetch plus local repo files. No project, amount, date or location was invented. A blank field means the source does not state it.

## Files
- `projects_inventory.csv`: 37 projects, with the requested fields plus `attachability_score`.
- `shortlist.md`: the 5 best attachment targets, with indicative add-on costs.

## Scoring (attachability_score 0-3)
- **3:** active or recent, Bekaa or Baalbek-Hermel-specific, implemented by or with Lebanese actors (NNGO, municipality or cooperative), clear hook.
- **2:** meets most of these. Typical gaps: national scope, implementer not named, amount unknown, or an INGO implementer.
- **1:** weak fit (national or unspecified geography, no clear entry point) or status unverified.
- **0:** closed. Kept as a precedent only.

A known amount was used as a tie-breaker. `recency_ok = yes` means the project was announced or approved in roughly the last 6 months (since about May 2026). Older but still active items are kept and marked `no`.

## Sources searched
- **World Bank:** LEAP FAQ (Feb 2026); GATE P180334 (CDR ESCP Feb 2026, GM Jun 2026); the UNDP press release on the GATE matching grants (13 Oct 2026); the Health Resilience Project (closed 31 Mar 2026, so excluded); Pandemic Fund One Health.
- **UNDP:** stabilization micro-grants 2026; KfW Hermel story (Jun 2026); KfW/LARI seedlings (Jun 2026); France cooperatives (Nov 2025).
- **FAO:** news list from May to Nov 2026; ERP 2026-2028; Denmark land reclamation (2025); Italy EUR 5M (Jul 2026).
- **EU/EEAS:** EUR 32M programme (19 May 2026) and AFD BALADNA page; six agreements incl. EUR 25M (14 Jan 2026); EU/WFP/FAO farmer cash programme.
- **AFD:** BALADNA; SAQIRH II; GTAI notice for AFD/Solidarites International in Baalbek-Hermel.
- **Water:** Litani River Authority site; SPNL/DIMFE Upper Litani; AICS (Zahle WWTP TED notice; Oikos CARE IATI record); SDC Bekaa Water Management Programme; UNICEF SitRep No. 5 (Jul 2026); WaSH sector At a Glance (Jan-Sep 2026, snippet only).
- **Health:** LHF/CBPF project extract in the repo (2025-2026 projects with Bekaa or Baalbek-Hermel in the title); MSF Bekaa article (Aug 2026); Amel; Anera logs; WHO and UNFPA appeals (already in the registry as F006/F007 and not duplicated here).
- **Ministry of Agriculture:** the national response plan weekly reports are cited in press (Weekly Report No. 5, 4 May 2026). They are needs and damage reports, not funded projects, so they are not inventoried.
- **Also read:** the existing registry (`lebanon-hhc-policy/data/registry/funding_registry.csv`). Overlaps: F003 = P06, F008 = P17, F019 = P04, F020 = P05.

## Not found / gaps
- **No funded Bekaa project with a soil-contamination or health-screening component.** The CNRS-L / MoE war-impact study (launched 24 Apr 2026) and the Amel/AUB Turabna soil pilot (May 2026) cover the South only. No Bekaa follow-on project was found.
- **Litani River Authority:** no new donor-funded project in 2026 for the upper basin (Bekaa) was found, apart from SPNL/DIMFE.
- **Amounts not disclosed:** UNDP/KfW Hermel, AFD/Solidarites International, the ILO grapes project, MSF, Anera and the EU farmer cash programme. The UNDP micro-grants funder is not stated.
- **Not found:** UNFPA or WHO activity lists specific to Bekaa; the Health Sector 4W by governorate.
- **SDC Bekaa Water Management Programme:** status and budget for 2026 not confirmed. The project database page could not be read.
- **LHF project end dates and districts:** not in the CBPF export. Amounts are full budgets and often cover several governorates.

## Caveats
- Several pages were read through an extraction model (WebFetch). Verify key numbers against the source before citing them.
- Costs in `shortlist.md` use the given unit prices with illustrative sample counts. They are not quotes.
- `contact_route` lists official project or organization pages only. The one email (GRM.LEAP@cdr.gov.lb) is copied from the World Bank LEAP FAQ.
