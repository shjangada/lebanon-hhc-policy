"""2.7-2.9 governance and state-capacity registry updates from the primary-source checks (transcribed/primary_checks.csv, moph_budget_2026.csv).
- SC01 (WGI Government Effectiveness 29.9, 2025): verified against the World Bank API (primary).
- W19 (IMF public minimum wage LBP 675,000): verified against the IMF TA report (it contains no health-worker pay figures).
- SC13: MoPH 2026 allocation from the Citizen Budget 2026 (LBP bn; USD only as a flagged conversion at the budget rate 89,500 LBP/USD).
- admin_capacity_index: NOT computable at district level: the UN-Habitat RMA publishes only aggregates for a national sample of 38 municipalities (docs/ADMIN_CAPACITY_INDEX.md),
  so governance_capacity.csv stays a mock scenario input. The real LHF national-NGO share replaces the mock `share_funds_managed_locally` baseline (see lhf_allocations)."""
from __future__ import annotations

import pandas as pd

from .common import ROOT

REG = ROOT / "data" / "registry"


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
    return {"registry_rows_updated": changed, "admin_capacity_index": "not computable at district level (see docs/ADMIN_CAPACITY_INDEX.md)"}
