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

from .common import DERIVED, DISTRICT_LABEL, GOVERNORATE_LABEL, RAW, log_unmatched, lrp_table, provenance

UNHCR_ACTIVE = 889_625          # UNHCR active records of Syrians, 30 Jun 2026 (S10)
LRP_SYRIANS = 1_120_000         # LRP 2026 planning figure (S11)
PREGNANT_PER_WOMAN = 0.041
UPSAMPLE = 10                   # WorldPop 1 km -> 100 m cells so sub-pixel cadasters get an area share


def _admin3():
    z = zipfile.ZipFile(RAW / "admin_boundaries" / "lbn_admin_boundaries.geojson.zip")
    feats = json.loads(z.read("lbn_admin3.geojson"))["features"]
    # 'Litige' = disputed areas in the boundary file, not cadasters
    return [f for f in feats if f["properties"]["adm2_name"] in DISTRICT_LABEL and f["properties"]["adm3_name"] not in ("Litige", "Conflict")]


def _admin3_all():
    z = zipfile.ZipFile(RAW / "admin_boundaries" / "lbn_admin_boundaries.geojson.zip")
    return json.loads(z.read("lbn_admin3.geojson"))["features"]


def _cad_row(f) -> dict:
    p, c = f["properties"], shape(f["geometry"]).centroid
    return {"cadaster_id": p["adm3_pcode"], "cadaster_name": p["adm3_name"], "cadaster_name_ar": p.get("adm3_name1"),
            "district": DISTRICT_LABEL.get(p["adm2_name"], p["adm2_name"]), "district_pcode": p["adm2_pcode"], "district_name_cod": p["adm2_name"],
            "governorate": GOVERNORATE_LABEL.get(p["adm1_name"], p["adm1_name"]), "governorate_pcode": p["adm1_pcode"],
            "lat": round(c.y, 5), "lon": round(c.x, 5), "area_km2": round(float(p.get("area_sqkm") or 0), 3)}


def build_cadasters() -> pd.DataFrame:
    df = pd.DataFrame([_cad_row(f) for f in _admin3()]).sort_values(["district", "cadaster_name"]).reset_index(drop=True)
    return provenance(df, "OCHA COD-AB Lebanon admin 3 (D01)", "2026-01-26", "verified", "https://data.humdata.org/dataset/cod-ab-lbn", "D01")


def build_cadasters_national() -> pd.DataFrame:
    df = pd.DataFrame([_cad_row(f) for f in _admin3_all()]).sort_values(["governorate", "district", "cadaster_name"]).reset_index(drop=True)
    return provenance(df, "OCHA COD-AB Lebanon admin 3, national (D01)", "2026-01-26", "verified", "https://data.humdata.org/dataset/cod-ab-lbn", "D01")


def build_crosswalk() -> pd.DataFrame:
    """Name -> p-code crosswalk for admin 1-3 (English, Arabic, project label). Matching elsewhere must go through p-codes, never free text."""
    rows = []
    seen = set()
    for f in _admin3_all():
        p = f["properties"]
        for lvl, code, names, parent in (("admin1", p["adm1_pcode"], [p["adm1_name"], p.get("adm1_name1"), GOVERNORATE_LABEL.get(p["adm1_name"])], "LB"),
                                         ("admin2", p["adm2_pcode"], [p["adm2_name"], p.get("adm2_name1"), DISTRICT_LABEL.get(p["adm2_name"])], p["adm1_pcode"]),
                                         ("admin3", p["adm3_pcode"], [p["adm3_name"], p.get("adm3_name1")], p["adm2_pcode"])):
            for n in names:
                if n and (lvl, code, n) not in seen:
                    seen.add((lvl, code, n))
                    rows.append({"level": lvl, "name": n, "pcode": code, "parent_pcode": parent, "source": "COD-AB admin boundaries (D01)"})
    return pd.DataFrame(rows)


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
    pal = next(c for c in summ.columns if c.startswith("TOTAL PALESTINIANS (2026)"))
    mig = next(c for c in summ.columns if c.startswith("Migrants (2026)"))
    out = summ[["District", "TOTAL LEBANESE (2026)", "TOTAL SYRIANS (2026)", "TOTAL POPULATION (2026)", pal, mig]].copy()
    out.columns = ["lrp_district", "lebanese", "syrians", "total", "palestinians", "migrants"]
    ret = lrp_table("IDP-Return-Origin-Destination")
    out["returnees_lrp"] = out.lrp_district.map(dict(zip(ret["District"], pd.to_numeric(ret["Total return"], errors="coerce"))))
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
            "pop_lebanese": (L.lebanese * w).round().astype(int).values, "pop_syrians_lrp": (L.syrians * w).round().astype(int).values,
            "pop_palestinians": (L.palestinians * w).round().astype(int).values, "pop_migrants": (L.migrants * w).round().astype(int).values,
            "dtm_idps_present_district": float(idp[lname]), "returnees_lrp_district": float(L.returnees_lrp) if pd.notna(L.returnees_lrp) else np.nan,
            "displaced_syrians_registered": (L.syrians * reg_ratio * w).round().astype(int).values,
            "unregistered_workers_est": (L.syrians * (1 - reg_ratio) * w).round().astype(int).values}))
    pop = pd.concat(out, ignore_index=True)
    pop.insert(3, "pregnant_est", (pop.women_15_49 * PREGNANT_PER_WOMAN).round().astype(int))
    pop = pop[["cadaster_id", "population_total", "women_15_49", "pregnant_est", "displaced", "displaced_syrians_registered", "unregistered_workers_est",
               "pop_lebanese", "pop_syrians_lrp", "pop_palestinians", "pop_migrants", "dtm_idps_present_district", "returnees_lrp_district"]]
    return provenance(pop, "LRP 2026 population package (D03) + WorldPop 2025 1 km (D08) + IOM DTM round " + idp.attrs["round_date"] + " (D04); "
                      "Syrian registered/unregistered split (LRP planning figure vs UNHCR records, S11) and the within-district spread of every group are assumptions", "2026-10-31", "assumption", source_id="D03+D04+D08")


def run() -> dict:
    DERIVED.mkdir(parents=True, exist_ok=True)
    cad = build_cadasters()
    pop = build_population(cad)
    empty = set(pop[pop.population_total <= 0].cadaster_id)            # no WorldPop mass: nobody to prioritise, and Need Score divides by population
    cad, pop = cad[~cad.cadaster_id.isin(empty)], pop[~pop.cadaster_id.isin(empty)]
    cad.to_csv(DERIVED / "cadasters.csv", index=False)
    pop.to_csv(DERIVED / "population.csv", index=False)
    nat = build_cadasters_national()
    nat.to_csv(DERIVED / "cadasters_national.csv", index=False)
    build_crosswalk().to_csv(DERIVED / "name_crosswalk.csv", index=False)
    feats = [f for f in _admin3() if f["properties"]["adm3_pcode"] in set(cad.cadaster_id)]
    (DERIVED / "cadasters.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": f["geometry"], "properties": {"cadaster_id": f["properties"]["adm3_pcode"], "cadaster_name": f["properties"]["adm3_name"]}} for f in feats]}))
    log_unmatched("cadasters_population", "admin3", list(empty), "dropped: zero WorldPop population in polygon")
    return {"cadasters": len(cad), "dropped_empty": len(empty), "population_total": int(pop.population_total.sum())}
