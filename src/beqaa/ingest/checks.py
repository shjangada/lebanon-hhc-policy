"""Sanity checks on the processed data (section 5 of the ingest handoff). They PRINT warnings; nothing is auto-corrected."""
from __future__ import annotations

import csv

import pandas as pd
from scipy.stats import spearmanr

from .cadasters_population import _lrp_district
from .common import DISTRICT_LABEL, PROCESSED, RAW


def population_vs_lrp() -> pd.DataFrame:
    pop = pd.read_csv(PROCESSED / "population.csv", dtype={"cadaster_id": str}).merge(pd.read_csv(PROCESSED / "cadasters.csv", dtype={"cadaster_id": str})[["cadaster_id", "district"]])
    lrp = _lrp_district().set_index("lrp_district")
    inv = {v: k for k, v in DISTRICT_LABEL.items()}
    s = pop.groupby("district").population_total.sum()
    t = pd.DataFrame({"district": s.index, "cadaster_sum": s.values, "lrp_total": [lrp.loc[inv[d], "total"] for d in s.index]})
    t["diff_pct"] = (t.cadaster_sum / t.lrp_total - 1) * 100
    t["within_5pct"] = t.diff_pct.abs() <= 5
    return t


def facilities_vs_osm() -> dict:
    import json
    import zipfile
    z = zipfile.ZipFile(RAW / "facilities" / "hotosm_osm" / "hotosm_lbn_health_facilities_osm_geojson.zip")
    osm = sum(1 for f in json.loads(z.read("health_facilities.geojson"))["features"] if (f["properties"].get("amenity") or f["properties"].get("healthcare")) in ("hospital", "clinic", "centre", "doctors"))
    fac = pd.read_csv(PROCESSED / "facilities.csv")
    return {"osm_health_facilities_nationally_of_modelled_types": osm, "in_five_districts": len(fac), "share": round(len(fac) / osm, 3)}


def travel_time_vs_hdx() -> dict:
    """District share of population within 30 min of a PHC: our straight-line model (PHC type only) vs the HDX accessibility file. Spearman rho."""
    tt = pd.read_csv(PROCESSED / "travel_time.csv", dtype={"cadaster_id": str, "facility_id": str})
    fac = pd.read_csv(PROCESSED / "facilities.csv", dtype={"facility_id": str})
    pop = pd.read_csv(PROCESSED / "population.csv", dtype={"cadaster_id": str})[["cadaster_id", "population_total"]]
    cad = pd.read_csv(PROCESSED / "cadasters.csv", dtype={"cadaster_id": str})[["cadaster_id", "district"]]
    near = tt[tt.facility_id.isin(fac[fac["type"] == "PHC"].facility_id)].groupby("cadaster_id").minutes.min().rename("min_phc")
    d = cad.merge(pop).merge(near, left_on="cadaster_id", right_index=True, how="left")
    ours = d.groupby("district").apply(lambda g: float((g.population_total * (g.min_phc.fillna(1e9) <= 30)).sum() / g.population_total.sum()), include_groups=False)
    hdx = pd.read_csv(PROCESSED / "travel_time_hdx_access.csv")
    rows = {}
    for r in csv.DictReader(open(RAW / "travel_time" / "accessibility" / "LBN_primary_healthcare_access_wide.csv", encoding="utf-8-sig")):
        if r["admin_level"] == "ADM2" and r["range"] == "1800":
            rows[r["name"]] = float(r["population_share"]) / 100.0
    hd = pd.Series({DISTRICT_LABEL.get(k, k): v for k, v in rows.items() if DISTRICT_LABEL.get(k, k) in ours.index})
    both = pd.DataFrame({"ours_share_within_30min_phc": ours, "hdx_share_within_30min_phc": hd}).dropna()
    rho = float(spearmanr(both.iloc[:, 0], both.iloc[:, 1])[0]) if len(both) > 2 else float("nan")
    return {"rho": rho, "n_districts": len(both), "table": both.round(3)}


def run() -> dict:
    p = population_vs_lrp()
    f = facilities_vs_osm()
    t = travel_time_vs_hdx()
    warns = []
    if not p.within_5pct.all():
        warns.append("population: some district sums are not within +-5% of the LRP total")
    if f["share"] < 0.1:
        warns.append("facilities: the five districts hold a small share of the national OSM facility count (check scope)")
    if not (t["rho"] > 0.5):
        warns.append(f"travel time: our ranking disagrees with HDX accessibility (rho={t['rho']:.2f}); PHCC positions are village centroids and few facilities have a dated status")
    for w in warns:
        print("WARNING:", w)
    return {"population_max_abs_diff_pct": round(float(p.diff_pct.abs().max()), 3), "facilities": f, "travel_time_rho": round(t["rho"], 2), "warnings": len(warns)}
