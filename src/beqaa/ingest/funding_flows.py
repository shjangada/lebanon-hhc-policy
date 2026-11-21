"""1.6 funding_flows: OCHA FTS incoming funding to Lebanon, by year, cluster and recipient organisation type.

FTS recipient types are coarse (NGOs, Multilateral Organizations, Governments, Pooled Funds, Red Cross/Crescent, Private): they do NOT split national from international
NGOs. 'share_to_government' is therefore a lower bound on funding reaching Lebanese actors; the national-NGO share comes from the CBPF/LHF data (lhf_allocations.py).
Amounts are USD (amountUSD); rows with no amount are skipped and counted."""
from __future__ import annotations

import csv

import pandas as pd

from .common import PROCESSED, RAW, provenance

TYPE_MAP = {"NGOs": "NGO (national/international not distinguished)", "Multilateral Organizations": "UN / multilateral", "Governments": "Government",
            "Pooled Funds": "Pooled fund", "Red Cross/Red Crescent Organizations": "Red Cross / Red Crescent", "Private Organizations": "Private"}


def build() -> pd.DataFrame:
    rows = list(csv.DictReader(open(RAW / "funding_flows" / "fts" / "fts_incoming_funding_lbn.csv", encoding="utf-8-sig")))
    recs = []
    for r in rows:
        try:
            amt = float(r["amountUSD"])
        except ValueError:
            continue
        types = [t for t in dict.fromkeys(x.strip() for x in r["destOrganizationTypes"].split(",")) if t]
        clusters = [c for c in dict.fromkeys(x.strip() for x in r["destGlobalClusters"].split(",")) if c] or ["Not specified"]
        yr = r["budgetYear"] or (r["date"][:4] if r["date"] else "")
        if not yr:
            continue
        for t in types or ["Not specified"]:
            for c in clusters:
                recs.append({"year": int(yr), "cluster": c, "recipient_type": TYPE_MAP.get(t, t), "usd": amt / (len(types) or 1) / len(clusters)})   # split evenly across tags
    d = pd.DataFrame(recs).groupby(["year", "cluster", "recipient_type"], as_index=False).usd.sum()
    tot = d.groupby(["year", "cluster"]).usd.transform("sum")
    d["share_of_cluster_year"] = d.usd / tot
    return provenance(d, "OCHA FTS Lebanon incoming funding (fts_incoming_funding_lbn.csv); multi-tag rows split evenly", "2026-11-20", "verified",
                      "https://data.humdata.org/dataset/lbn-requirements-and-funding-data", "D06")


def dependency_series(d: pd.DataFrame, cluster: str = "Health") -> pd.DataFrame:
    """Share of funding by recipient type per year (dependency chart); government share = lower bound on Lebanese-actor share."""
    x = d[d.cluster == cluster].pivot_table(index="year", columns="recipient_type", values="usd", aggfunc="sum", fill_value=0.0)
    x["total_usd"] = x.sum(axis=1)
    x["share_to_government"] = x.get("Government", 0) / x.total_usd
    x["share_to_un_multilateral"] = x.get("UN / multilateral", 0) / x.total_usd
    return x.reset_index()


def run() -> dict:
    d = build()
    d.to_csv(PROCESSED / "funding_flows.csv", index=False)
    ds = dependency_series(d)
    ds.to_csv(PROCESSED / "funding_flows_health_dependency.csv", index=False)
    return {"rows": len(d), "years": sorted(d.year.unique().tolist()), "health_usd": float(d[d.cluster == "Health"].usd.sum())}
