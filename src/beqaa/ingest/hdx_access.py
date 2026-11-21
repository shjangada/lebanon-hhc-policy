"""1.3 cross-check for M1: HDX accessibility indicators (PHC and hospital access by admin level and travel-time range).

Reshapes LBN_{primary_healthcare,hospitals}_access_wide.csv to (admin level, area) x category x minutes -> share of population within that time.
The model's own travel times (processed/travel_time.csv: cadaster x facility, straight-line x 1.3 / 40 km/h, an ASSUMPTION) are compared with this file at district level
(Spearman rho) by `agreement()`. This file is NOT the M1 input; the cadaster x facility schema is."""
from __future__ import annotations

import csv

import pandas as pd

from .common import PROCESSED, RAW, provenance


def build() -> pd.DataFrame:
    out = []
    for cat, fn in (("PHC", "LBN_primary_healthcare_access_wide.csv"), ("hospital", "LBN_hospitals_access_wide.csv")):
        for r in csv.DictReader(open(RAW / "travel_time" / "accessibility" / fn, encoding="utf-8-sig")):
            if r["range_type"] != "TIME":
                continue
            out.append({"admin_level": r["admin_level"], "area": r["name"], "category": cat, "minutes": float(r["range"]) / 60.0, "population": float(r["population"] or 0),
                        "women_childbearing_population": float(r["women_childbearing_population"] or 0),
                        "share_population_within": float(r.get("population_share") or "nan") if "population_share" in r else float("nan")})
    d = pd.DataFrame(out)
    return provenance(d, "HDX Lebanon accessibility indicators (PHC and hospital access)", "2026-02-25", "verified", "https://data.humdata.org/dataset/lebanon-accessibility-indicators", "D07")


def run() -> dict:
    d = build()
    d.to_csv(PROCESSED / "travel_time_hdx_access.csv", index=False)
    return {"rows": len(d), "levels": sorted(d.admin_level.unique().tolist())}
