# Beqaa (Bekaa + Baalbek-Hermel) health funding and partner presence

Compiled 2026-11-21. No values were estimated or imputed. Every number has a source URL.

## Access constraints
Both shells' egress proxies block data.humdata.org, data.unhcr.org and cbpfapi.unocha.org, so no direct downloads were possible. Sources were read via WebFetch (text extraction). Image-based PDFs (Health Sector Dashboards Mid-Year 2026 and End-of-Year 2025) came back as binary and could not be read. The LHF data comes from the CBPF project summary already in the repo (lebanon-hhc-policy/data/raw/lhf/global_cbpf_project_summary.csv; source: HDX cbpf-allocations-and-contributions).

## Files
- `beqaa_funding_by_recipient_type.csv`
  - LHF (CBPF) health-titled projects 2024-2026 whose TITLE names a Bekaa or Baalbek-Hermel location, aggregated by OrganizationType. National LHF health totals are included as a denominator.
  - Also includes national LRP and Aid-Tracking health totals.
  - CAVEATS:
    1. Amounts are FULL project budgets. Multi-governorate projects are not apportioned.
    2. The CBPF export has no location or cluster field. Its text fields (summary, activities) are empty for 2024-26, so geography and sector come from title keywords only. Projects in Beqaa that do not name it in the title are missed.
    3. "Health" here includes multi-sector projects and one WASH project (INTERSOS, CBPF-LEB-25-S-INGO-37783). Drop it if you need a strict definition.
  - Result: of Beqaa-titled LHF health money, a National NGO received $199,993 in 2025 (Embrace); every other dollar went to INGOs.
    - 2024: $3.20M INGO, $0 NNGO
    - 2025: $3.58M INGO, $0.20M NNGO
    - 2026: $2.45M INGO, $0 NNGO
    - No UN agency or government recipients appear among these projects.
- `beqaa_health_partners.csv`
  - Rows 1-39: operators of the 64 MoPH-network PHCCs in Bekaa (38) and Baalbek-Hermel (26), transcribed from the MoPH PHCC list of 16/04/2026, pp. 18-22. All are Lebanese actors: MoPH, MoSA, municipalities, Lebanese NGOs, religious institutions and the Lebanese Red Cross.
    - Note: the MoPH Annual Dashboard 2025 reports 37 Bekaa and 28 Baalbek-Hermel PHCCs, so the transcription (done by an extraction model) may have missed rows. Verify against the PDF.
  - The remaining rows are INGO, NNGO and UN partners identified from LHF project titles, the Health Sector contact list (Jan 2026) and MSF (Aug 2026).
  - `women_led` = unknown for all rows. No org-site verification was done.
  - Arabic names are kept as listed, with a fix for PDF ligature artifacts (e.g. "اال" -> "الا").
- `raw/moph_phcc_list_2026-04-16_bekaa_bh_transcribed.csv`: facility-level rows (page, center, caza, town, operator, inferred type, malnutrition-centre flag).
- `raw/lhf_lebanon_projects_extract.csv`: all 545 Lebanon CBPF projects (2015-2026), with title-based location and health flags.

## Not available (searched)
- **Health Sector 4W/5W by governorate, 2025-26:** not found as a machine-readable file. HDX was not reachable. On data.unhcr.org, the Health Sector "3W" items are old (COVID service mapping, March 2020). The Inter-Agency PHC Masterlist (25 March 2025) was listed but not fetched or read.
- **Health Sector At a Glance Q3 2026 (doc 124710):** national only. Appeal $188.8M, received $72.0M, carry-over $9.1M. Flash Appeal: $74.2M required, $41.3M received. Addendum: $49.9M required, $0.65M received. 76 PHC facilities engaged in outreach. No governorate or partner split.
- **LRP Funding Update Jan-Sep 2026 (doc 124737):** Health received $113.99M, carry-over $10.15M, available $124.15M, appeal $312.98M. Recipients are listed by name only, with no type and no governorate.
- **UN RCO Aid Tracking Q3 2025:** Health received $65.8M, appeal $278.7M, 39% funded. There is no governorate, channel or recipient-type breakdown and no localization figure. A 2026 edition was not found on the page.
- **LRP Addendum Sep-Dec 2026 (local PDF, pp. 26-27):** names Bekaa and Baalbek-Hermel as health priority areas but gives no partner or funding figures by governorate.
- **Health Sector contacts, Jan 2026 (doc 90610):** MEDAIR is the Baalbek-Hermel sub-national co-coordinator. No organization is listed for Bekaa.

## Implication for the KPI
A Beqaa-specific "share of health money controlled by Lebanese actors" cannot be computed from published funding data. The only geo-tagged proxy is LHF title-based: about 0-5% to national NGOs (2025: 0.20 / 3.78 = 5.3%; 2024 and 2026: 0%). On the service-delivery side, 100% of MoPH-network PHCCs in Beqaa are run by Lebanese actors, but their funding sources are not published.
