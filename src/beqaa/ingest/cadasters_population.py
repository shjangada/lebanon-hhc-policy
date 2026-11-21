"""Cadasters (admin 3) and population for the five Beqaa districts.

cadasters: COD-AB admin-3 areas (D01), centroid lat/lon. District names use project labels (El Hermel -> Hermel).
population: spatial distribution from WorldPop 2025 1 km age/sex (D08), rescaled so each district matches the LRP 2026
planning total (D03). Group splits:
  displaced                     = latest IOM DTM round, IDPs present by district (D04), spread over cadasters by population
  displaced_syrians_registered  = LRP Syrian estimate x (UNHCR active records / LRP Syrian planning figure), national ratio  [ASSUMPTION]
  unregistered_workers_est      = LRP Syrian estimate x (1 - that ratio)                                                   [ASSUMPTION]
  women_15_49                   = LRP age tables x female share per district, modulated by WorldPop cadaster women share
  pregnant_est                  = women_15_49 x 0.041 (UNFPA: ~16,000 pregnant of 390,000 women)                           [ASSUMPTION]
Syrians/unregistered are spread over cadasters in proportion to total population: no cadaster-level source exists.
"""
from __future__ import annotations

import csv
import json
import zipfile

import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from shapely.geometry import shape

from .common import DERIVED, DISTRICT_LABEL, GOVERNORATE_LABEL, RAW, lrp_table, provenance

UNHCR_ACTIVE = 889_625          # UNHCR active records of Syrians, 30 Jun 2026 (S10)
LRP_SYRIANS = 1_120_000         # LRP 2026 planning figure (S11)
PREGNANT_PER_WOMAN = 0.041
UPSAMPLE = 10                   # WorldPop 1 km -> 100 m cells so sub-pixel cadasters get an area share


def _admin3():
    z = zipfile.ZipFile(RAW / "admin_boundaries" / "lbn_admin_boundaries.geojson.zip")
    feats = json.loads(z.read("lbn_admin3.geojson"))["features"]
    # 'Litige' = disputed areas in the boundary file, not cadasters
    return [f for f in feats if f["properties"]["adm2_name"] in DISTRICT_LABEL and f["properties"]["adm3_name"] not in ("Litige", "Conflict")]


def build_cadasters() -> pd.DataFrame:
    rows = []
    for f in _admin3():
        p, c = f["properties"], shape(f["geometry"]).centroid
        rows.append({"cadaster_id": p["adm3_pcode"], "cadaster_name": p["adm3_name"], "district": DISTRICT_LABEL[p["adm2_name"]],
                     "governorate": GOVERNORATE_LABEL[p["adm1_name"]], "lat": round(c.y, 5), "lon": round(c.x, 5)})
    df = pd.DataFrame(rows).sort_values(["district", "cadaster_name"]).reset_index(drop=True)
    return provenance(df, "OCHA COD-AB Lebanon admin 3 (D01)", "2026-01-26", "verified", "https://data.humdata.org/dataset/cod-ab-lbn")


def _worldpop_zonal(feats) -> pd.DataFrame:
    zpath = RAW / "population" / "worldpop" / "lbn_agesex_structures_2025_CN_1km_R2025A_UA_v1.zip"
    names = zipfile.ZipFile(zpath).namelist()
    tot = [n for n in names if "_t_" in n and n.endswith(".tif")]
    women = [n for n in names if any(f"_f_{a:02d}_" in n for a in range(15, 50, 5)) and n.endswith(".tif")]
    assert len(women) == 7 and len(tot) >= 15, (len(women), len(tot))

    def read(name):
        with rasterio.open(f"/vsizip/{zpath}/{name}") as src:
            a = src.read(1).astype("float64")
            a[(a < 0) | ~np.isfinite(a)] = 0
            return a, src.transform, src.shape
    a0, tr, shp = read(tot[0])
    big_tr = tr * tr.scale(1 / UPSAMPLE, 1 / UPSAMPLE)
    ids = rasterize([(f["geometry"], i) for i, f in enumerate(feats)], out_shape=(shp[0] * UPSAMPLE, shp[1] * UPSAMPLE),
                    transform=big_tr, fill=-1, dtype="int32")

    def zonal(names_):
        s = sum(read(n)[0] for n in names_)
        up = np.kron(s, np.ones((UPSAMPLE, UPSAMPLE))) / UPSAMPLE ** 2
        m = ids >= 0
        return np.bincount(ids[m], weights=up[m], minlength=len(feats))
    return pd.DataFrame({"cadaster_id": [f["properties"]["adm3_pcode"] for f in feats], "wp_total": zonal(tot), "wp_women_15_49": zonal(women)})


def _lrp_district() -> pd.DataFrame:
    summ = lrp_table("ALL POPULATION SUMMARY")
    out = summ[["District", "TOTAL LEBANESE (2026)", "TOTAL SYRIANS (2026)", "TOTAL POPULATION (2026)"]].copy()
    out.columns = ["lrp_district", "lebanese", "syrians", "total"]
    shares = {}
    for sheet, key in (("LEBANESE", "lebanese"), ("SYRIAN", "syrians")):
        t = lrp_table(sheet)
        age = [c for c in t.columns if c in ("15 - 19", "20 - 24", "25 - 29", "30 - 34", "35 - 39", "40 - 44", "45 - 49")]
        assert len(age) == 7, age
        tot = t[[c for c in t.columns if c in ("TOTAL LEBANESE", "Syrian_Est")][0]].astype(float)
        fem = t[[c for c in t.columns if c.startswith("All ") and c.endswith("Female")][0]].astype(float)
        shares[key] = pd.Series((t[age].astype(float).sum(axis=1) / tot * fem / tot).values, index=t["District"])
    out["w_share_leb"] = out.lrp_district.map(shares["lebanese"])
    out["w_share_syr"] = out.lrp_district.map(shares["syrians"])
    others = (out.total - out.lebanese - out.syrians).clip(lower=0)
    out["women_15_49"] = out.lebanese * out.w_share_leb + out.syrians * out.w_share_syr + others * out.w_share_leb   # others use the Lebanese ratio
    return out[out.lrp_district.isin(DISTRICT_LABEL)]


def _dtm_idps() -> pd.Series:
    rows = list(csv.DictReader(open(RAW / "population" / "iom_dtm" / "lbn-iom-dtm-from-api-admin-0-to-2.csv", encoding="utf-8-sig")))
    a2 = [r for r in rows if r["adminLevel"] == "2" and r["admin2Name"] in DISTRICT_LABEL]
    latest = max(r["reportingDate"] for r in a2)
    s = pd.Series({d: 0.0 for d in DISTRICT_LABEL})
    for r in a2:
        if r["reportingDate"] == latest and r["numPresentIdpInd"]:
            s[r["admin2Name"]] += float(r["numPresentIdpInd"])
    s.attrs["round_date"] = latest[:10]
    return s


def build_population(cad: pd.DataFrame | None = None) -> pd.DataFrame:
    feats = _admin3()
    wp = _worldpop_zonal(feats)
    lrp = _lrp_district().set_index("lrp_district")
    idp = _dtm_idps()
    cad = cad if cad is not None else build_cadasters()
    inv = {v: k for k, v in DISTRICT_LABEL.items()}
    df = cad[["cadaster_id", "district"]].merge(wp, on="cadaster_id")
    df["lrp_name"] = df.district.map(inv)
    reg_ratio = UNHCR_ACTIVE / LRP_SYRIANS
    out = []
    for lname, g in df.groupby("lrp_name"):
        L = lrp.loc[lname]
        w = g.wp_total / g.wp_total.sum()                                  # population distribution inside the district
        pop_total = L.total * w
        wp_share = g.wp_women_15_49 / g.wp_total.replace(0, np.nan)
        mod = (wp_share / (g.wp_women_15_49.sum() / g.wp_total.sum())).fillna(1.0)        # cadaster women share relative to district
        women = pop_total * (L.women_15_49 / L.total) * mod
        women = women * (L.women_15_49 * w.sum() / women.sum())                # re-normalise to the LRP district women total
        out.append(pd.DataFrame({
            "cadaster_id": g.cadaster_id.values, "population_total": pop_total.round().astype(int).values,
            "women_15_49": women.round().astype(int).values,
            "displaced": (idp[lname] * w).round().astype(int).values,
            "displaced_syrians_registered": (L.syrians * reg_ratio * w).round().astype(int).values,
            "unregistered_workers_est": (L.syrians * (1 - reg_ratio) * w).round().astype(int).values}))
    pop = pd.concat(out, ignore_index=True)
    pop.insert(3, "pregnant_est", (pop.women_15_49 * PREGNANT_PER_WOMAN).round().astype(int))
    pop = pop[["cadaster_id", "population_total", "women_15_49", "pregnant_est", "displaced", "displaced_syrians_registered", "unregistered_workers_est"]]
    return provenance(pop, "LRP 2026 population package (D03) + WorldPop 2025 1 km (D08) + IOM DTM round " + idp.attrs["round_date"] + " (D04); "
                      "Syrian registered/unregistered split and women 15-49 allocation are assumptions", "2026-10-31", "assumption")


def run() -> dict:
    DERIVED.mkdir(parents=True, exist_ok=True)
    cad = build_cadasters()
    pop = build_population(cad)
    empty = set(pop[pop.population_total <= 0].cadaster_id)            # no WorldPop mass: nobody to prioritise, and Need Score divides by population
    cad, pop = cad[~cad.cadaster_id.isin(empty)], pop[~pop.cadaster_id.isin(empty)]
    cad.to_csv(DERIVED / "cadasters.csv", index=False)
    pop.to_csv(DERIVED / "population.csv", index=False)
    return {"cadasters": len(cad), "dropped_empty": len(empty), "population_total": int(pop.population_total.sum())}
