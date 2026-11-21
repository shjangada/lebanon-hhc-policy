"""2.7-2.9 governance and state-capacity registry updates from the primary-source checks (transcribed/primary_checks.csv, moph_budget_2026.csv).
- SC01 (WGI Government Effectiveness 29.9, 2025): verified against the World Bank API (primary).
- W19 (IMF public minimum wage LBP 675,000): verified against the IMF TA report (it contains no health-worker pay figures).
- SC13: MoPH 2026 allocation from the Citizen Budget 2026 (LBP bn; USD only as a flagged conversion at the budget rate 89,500 LBP/USD).
- admin_capacity_index: NOT computable at district level: the UN-Habitat RMA publishes only aggregates for a national sample of 38 municipalities (docs/ADMIN_CAPACITY_INDEX.md),
  so governance_capacity.csv stays a mock scenario input. The real LHF national-NGO share replaces the mock `share_funds_managed_locally` baseline (see lhf_allocations)."""
from __future__ import annotations

import pandas as pd

from .common import PROCESSED, ROOT, provenance

REG = ROOT / "data" / "registry"


DISTRICTS = ["Baalbek", "Hermel", "Zahle", "West Bekaa", "Rachaya"]


def build_governance(sc: pd.DataFrame) -> pd.DataFrame:
    """Replaces the mock district series with SOURCED national values applied to every district (no district spread is invented):
      admin_capacity_index  2025 = SC01 WGI Government Effectiveness 29.9/100 = 0.299 for all five districts (national anchor); 2026-2030 rows are PROJECTED (state_capacity caps gains at 0.05/yr)
      share_funds_managed_locally  2025 = LHF national-NGO share of project budgets that year (real, nationwide, one pooled fund); not projected here
      transparent_reporting  SCENARIO: False in 2025-2026, True from 2027 (a pre-agreed pilot rule: the consortium publishes quarterly spend). Not an observation.
    Districts therefore start identical: where district capacity differs is unknown until UN-Habitat RMA microdata exist (docs/DATA_REQUESTS.md)."""
    anchor = float(sc.loc[sc.id == "SC01", "value"].iloc[0]) / 100
    lhf = pd.read_csv(PROCESSED / "lhf_national_ngo_share_by_year.csv").set_index("year").national_ngo_share
    rows = []
    for d in DISTRICTS:
        rows.append({"district": d, "year": 2025, "projected": False, "admin_capacity_index": anchor, "share_funds_managed_locally": float(lhf.loc[2025]), "transparent_reporting": False})
        for y in range(2026, 2031):
            rows.append({"district": d, "year": y, "projected": True, "admin_capacity_index": anchor, "share_funds_managed_locally": float("nan"), "transparent_reporting": y >= 2027})
    return provenance(pd.DataFrame(rows), "National anchors applied to all districts: WGI GE 2025 (SC01), LHF national-NGO share 2025; transparent_reporting is a scenario rule; no district spread",
                      "2026-11-21", "partial", "https://api.worldbank.org/v2/country/LB/indicator/GOV_WGI_GE.SC?format=json", "SC01")


def run() -> dict:
    sc = pd.read_csv(REG / "state_capacity_sources.csv")
    wf = pd.read_csv(REG / "workforce_sources.csv")
    pc = pd.read_csv(ROOT / "transcribed" / "primary_checks.csv").set_index("item_id")
    changed = []
    if pc.loc["SC01", "match"] == "yes":
        sc.loc[sc.id == "SC01", ["status", "url"]] = ["verified_primary", pc.loc["SC01", "primary_url"]]
        changed.append("SC01")
    if pc.loc["W19", "match"] in ("yes", "partial"):
        wf.loc[wf.id == "W19", "status"] = "verified_primary (min wage only; no health-worker pay in the IMF report)"
        changed.append("W19")
    b = pd.read_csv(ROOT / "transcribed" / "moph_budget_2026.csv")
    mo = b[b["item"].str.contains("Ministry of Public Health", case=False, na=False) & (b.year == 2026)]
    if len(mo) and "SC13" not in set(sc.id):
        r = mo.iloc[0]
        sc.loc[len(sc)] = {"id": "SC13", "indicator": "MoPH allocation 2026 (Citizen Budget 2026)", "level": "national", "year": 2026, "value": float(r.value), "unit": r.currency,
                           "source": "Lebanon Citizen Budget 2026 (Institut des Finances), p. " + str(r.page), "url": "https://institutdesfinances.gov.lb/sites/default/files/2026-04/Citizen%20Budget%202026-Apr26-En-final_0.pdf",
                           "status": "verified", "notes": "LBP billions; budget exchange rate 89,500 LBP/USD (estimated). Does not contradict SC03 (2022, secondary): different year", "verified_on": "2026-11-21"}
        changed.append("SC13")
    sc.to_csv(REG / "state_capacity_sources.csv", index=False)
    wf.to_csv(REG / "workforce_sources.csv", index=False)
    build_governance(sc).to_csv(PROCESSED / "governance_capacity.csv", index=False)
    return {"governance_capacity": "real national anchors for all districts (no mock spread)", "registry_rows_updated": changed, "admin_capacity_index": "not computable at district level (see docs/ADMIN_CAPACITY_INDEX.md)"}
