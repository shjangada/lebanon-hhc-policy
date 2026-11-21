"""2.1 lhf_allocations: Lebanon Humanitarian Fund (CBPF fund id 71) project budgets by partner type and year (HDX global_cbpf_project_summary.csv).
National NGO share by year = Budget to 'National NGO' / total Budget. This is the baseline for 'share of funds managed locally' (governance_capacity); it is a share of one
pooled fund, NOT of all aid (compare funding_flows from FTS)."""
from __future__ import annotations

import csv

import pandas as pd

from .common import PROCESSED, RAW, provenance

SRC = RAW / "lhf" / "global_cbpf_project_summary.csv"
URL = "https://data.humdata.org/dataset/cbpf-allocations-and-contributions"


def build() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = [r for r in csv.DictReader(open(SRC, encoding="utf-8-sig")) if (r["PooledFundName"] or "").strip().lower() == "lebanon"]
    p = pd.DataFrame([{"year": int(r["AllocationYear"]), "partner_type": r["OrganizationType"], "allocation_type": r["AllocationType"], "organization": r["OrganizationName"],
                       "project_code": r["ChfProjectCode"], "budget_usd": float(r["Budget"] or 0), "project_status": r["ProjectStatus"]} for r in rows if r["AllocationYear"]])
    y = p.groupby(["year", "partner_type"], as_index=False).agg(budget_usd=("budget_usd", "sum"), projects=("project_code", "nunique"))
    tot = y.groupby("year").budget_usd.transform("sum")
    y["share_of_year"] = y.budget_usd / tot
    y = provenance(y, "OCHA CBPF project summary, Lebanon Humanitarian Fund (fund id 71)", "2026-11-21", "verified", URL, "F004/D01-CBPF")
    return y, provenance(p, "OCHA CBPF project summary, Lebanon Humanitarian Fund (project level, text fields dropped)", "2026-11-21", "verified", URL, "F004/D01-CBPF")


def nngo_share_by_year(y: pd.DataFrame) -> pd.DataFrame:
    s = y.pivot_table(index="year", columns="partner_type", values="budget_usd", aggfunc="sum", fill_value=0.0)
    s["total_usd"] = s.sum(axis=1)
    s["national_ngo_share"] = s.get("National NGO", 0) / s.total_usd
    return s.reset_index()


def run() -> dict:
    y, p = build()
    y.to_csv(PROCESSED / "lhf_allocations.csv", index=False)
    p.to_csv(PROCESSED / "lhf_projects.csv", index=False)
    s = nngo_share_by_year(y)
    s.to_csv(PROCESSED / "lhf_national_ngo_share_by_year.csv", index=False)
    last = s.iloc[-1]
    return {"projects": len(p), "years": f"{int(s.year.min())}-{int(s.year.max())}", "latest_year": int(last.year), "latest_nngo_share": round(float(last.national_ngo_share), 3)}
