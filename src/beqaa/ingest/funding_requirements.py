"""FTS requirements and funding for Lebanon (plans and clusters): % funded of the Flash Appeal, Health cluster etc. (HDX D06). Used on the landing page."""
from __future__ import annotations

import pandas as pd

from .common import PROCESSED, RAW, provenance


def build() -> pd.DataFrame:
    base = RAW / "funding_flows" / "fts"
    plans = pd.read_csv(base / "fts_requirements_funding_lbn.csv")
    plans = plans[plans.requirements.notna()].assign(cluster="All clusters (plan total)")[["name", "typeName", "year", "cluster", "requirements", "funding", "percentFunded"]]
    cl = pd.read_csv(base / "fts_requirements_funding_cluster_lbn.csv")
    cl = cl[cl.requirements.notna()].assign(typeName="Flash appeal / plan cluster")[["name", "typeName", "year", "cluster", "requirements", "funding", "percentFunded"]]
    d = pd.concat([plans, cl], ignore_index=True).rename(columns={"name": "plan", "typeName": "plan_type", "requirements": "requirements_usd", "funding": "funding_usd", "percentFunded": "percent_funded"})
    return provenance(d, "OCHA FTS requirements and funding, Lebanon (plans and clusters)", "2026-11-20", "verified", "https://data.humdata.org/dataset/lbn-requirements-and-funding-data", "D06")


def run() -> dict:
    d = build()
    d.to_csv(PROCESSED / "funding_requirements.csv", index=False)
    fa = d[(d.plan == "Lebanon Flash Appeal 2026") & (d.cluster == "All clusters (plan total)")]
    return {"rows": len(d), "flash_appeal_2026_percent_funded": None if fa.empty else float(fa.percent_funded.iloc[0])}
