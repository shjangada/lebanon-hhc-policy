"""Facilities and travel times from OSM health facilities (D02) placed in cadasters (D01).

LIMITATIONS (printed in facilities_coverage.csv): OSM has far fewer PHCs than the MoPH network (LRP counts 61 PHC centres in the five
districts; OSM tags only a handful as clinics), so M1 PHC access built on this file is UNDERSTATED until the MoPH facility locator
(S04) is added. capacity_weekly, status_2026 (open), offers_anc and in_mophnetwork are ASSUMPTIONS: no public source gives them.
Travel time = straight-line distance x 1.3 detour / 40 km/h (assumption; cross-check with HDX accessibility indicators D07).
"""
from __future__ import annotations

import json
import math
import zipfile

import openpyxl
import pandas as pd
from shapely.geometry import shape
from shapely.strtree import STRtree

from .cadasters_population import _admin3
from .common import DERIVED, DISTRICT_LABEL, RAW, log_unmatched, provenance

CAPACITY = {"hospital_hub": 2000, "PHC": 300}          # weekly consultations (assumption, same orders of magnitude as the mock)
TYPE_MAP = {"hospital": "hospital_hub", "clinic": "PHC", "centre": "PHC", "doctors": "PHC"}


def _osm():
    z = zipfile.ZipFile(RAW / "facilities" / "hotosm_osm" / "hotosm_lbn_health_facilities_osm_geojson.zip")
    return json.loads(z.read("health_facilities.geojson"))["features"]


MOPH = RAW / "facilities" / "moph_bekaa" / "moph_facilities_bekaa.csv"
MOPH_TYPE = {"PHCC": "PHC", "hospital_public": "hospital_hub", "hospital_private": "hospital_hub"}
MOPH_STATUS = {"functional": "open", "partially damaged": "partial"}


def build_facilities_moph(cad: pd.DataFrame | None = None) -> pd.DataFrame:
    """MoPH locator + 2025 PHC-network list (97 facilities in the five districts), replacing OSM as the facility base.
    Hospitals are located by their OSM-matched coordinates; PHCCs only by the village centroid in their MoPH address (coord_confidence=village, 1-5 km
    uncertainty) because no PHCC has a facility-level position. Status stays blank (unknown) unless a dated 2026 source names the facility."""
    feats = _admin3()
    geoms = [shape(f["geometry"]) for f in feats]
    pcodes = [f["properties"]["adm3_pcode"] for f in feats]
    tree = STRtree(geoms)
    keep = set(cad.cadaster_id) if cad is not None else set(pcodes)
    raw = pd.read_csv(MOPH)
    rows, dropped = [], []
    for r in raw.itertuples():
        facility = pd.notna(r.lat)
        lat, lon = (r.lat, r.lon) if facility else (r.village_lat, r.village_lon)
        if pd.isna(lat):
            dropped.append(f"{r.facility_id} ({r.village})")
            continue
        pt = shape({"type": "Point", "coordinates": [lon, lat]})
        hit = [i for i in tree.query(pt) if geoms[i].contains(pt) and pcodes[i] in keep]
        if not hit:
            dropped.append(f"{r.facility_id} ({r.village}): outside the five districts' cadasters")
            continue
        kind = MOPH_TYPE[r.type]
        fs = str(r.functional_status)
        st = next((v for k, v in MOPH_STATUS.items() if fs.startswith(k)), "")
        rows.append({"facility_id": r.facility_id, "name": r.name_en if isinstance(r.name_en, str) else r.name_ar, "type": kind, "cadaster_id": pcodes[hit[0]],
                     "lat": round(float(lat), 5), "lon": round(float(lon), 5), "capacity_weekly": CAPACITY[kind], "status_2026": st,
                     "offers_anc": True, "in_mophnetwork": r.moph_network == "yes", "osm_amenity": "", "name_ar": r.name_ar,
                     "functional_status": "" if fs == "unknown" else fs, "status_date": "" if pd.isna(r.status_date) else r.status_date,
                     "status_source": "" if pd.isna(r.status_source_url) else r.status_source_url,
                     "has_solar_backup": float("nan"), "power_source": "unknown", "hours_per_week": float("nan"),
                     "coord_confidence": r.coord_confidence if facility else "village", "moph_facility_type": r.type,
                     "assumed_fields": "capacity_weekly;offers_anc" + ("" if facility else ";location(village centroid)")})
    if dropped:
        log_unmatched("facilities_moph", "facility", dropped, "MoPH facility with no usable coordinate or outside the five districts")
    df = pd.DataFrame(rows)
    return provenance(df, "MoPH Health Facility Locator + MoPH PHC network list 27/03/2025 (62 network PHCCs, 6 public and 23 private hospitals); capacity and ANC offering are assumptions; PHCC position = village centroid",
                      "2026-11-21", "assumption", "https://www.moph.gov.lb/en/HealthFacilities/index/0/20379/8", "S04")


def build_facilities(cad: pd.DataFrame | None = None) -> pd.DataFrame:
    if MOPH.exists():
        return build_facilities_moph(cad)
    return build_facilities_osm(cad)


def build_facilities_osm(cad: pd.DataFrame | None = None) -> pd.DataFrame:
    feats = _admin3()
    geoms = [shape(f["geometry"]) for f in feats]
    pcodes = [f["properties"]["adm3_pcode"] for f in feats]
    tree = STRtree(geoms)
    keep = set(cad.cadaster_id) if cad is not None else set(pcodes)
    rows = []
    for f in _osm():
        p = f["properties"]
        kind = TYPE_MAP.get(p.get("amenity") or p.get("healthcare"))
        if not kind:
            continue
        g = shape(f["geometry"])
        pt = g if g.geom_type == "Point" else g.centroid
        hit = [i for i in tree.query(pt) if geoms[i].contains(pt) and pcodes[i] in keep]
        if not hit:
            continue
        name = p.get("name_en") or p.get("name") or p.get("name_latin") or f"unnamed {kind}"
        rows.append({"facility_id": "OSM-" + str(p["id"]).replace("/", "-"), "name": name, "type": kind, "cadaster_id": pcodes[hit[0]],
                     "lat": round(pt.y, 5), "lon": round(pt.x, 5), "capacity_weekly": CAPACITY[kind], "status_2026": "open",
                     "offers_anc": True, "in_mophnetwork": False, "osm_amenity": p.get("amenity") or p.get("healthcare"), "name_ar": p.get("name_ar"),
                     "functional_status": "", "status_date": "", "status_source": "", "has_solar_backup": float("nan"), "power_source": "unknown",
                     "hours_per_week": float("nan"),
                     "assumed_fields": "capacity_weekly;offers_anc;in_mophnetwork"})
    df = pd.DataFrame(rows).drop_duplicates("facility_id").reset_index(drop=True)
    return provenance(df, "OSM health facilities via HOT/HDX (D02); capacity, status, ANC and MoPH-network flags are assumptions", "2026-11-15", "assumption",
                      "https://data.humdata.org/dataset/hotosm_lbn_health_facilities", "D02")


def coverage(fac: pd.DataFrame, cad: pd.DataFrame) -> pd.DataFrame:
    ws = openpyxl.load_workbook(RAW / "population" / "lrp_2026" / "05.-2026-lrp-population-package.xlsx", data_only=True, read_only=True)["PHC-MOPH Network"]
    lrp = {r[0]: r[1] for r in ws.iter_rows(values_only=True) if r[0] in DISTRICT_LABEL}
    f = fac.merge(cad[["cadaster_id", "district"]], on="cadaster_id")
    out = []
    for real, label in DISTRICT_LABEL.items():
        n = int((f[(f.district == label)].type == "PHC").sum())
        out.append({"district": label, "phc_in_list": n, "phc_in_mophnetwork_lrp2026": int(lrp[real]), "coverage": round(n / lrp[real], 2),
                    "hospitals_in_list": int((f[(f.district == label)].type == "hospital_hub").sum())})
    c = pd.DataFrame(out)
    c.loc[len(c)] = ["TOTAL", c.phc_in_list.sum(), c.phc_in_mophnetwork_lrp2026.sum(), round(c.phc_in_list.sum() / c.phc_in_mophnetwork_lrp2026.sum(), 2), c.hospitals_in_list.sum()]
    return c


def _hav(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(x))


def build_travel_time(cad: pd.DataFrame, fac: pd.DataFrame) -> pd.DataFrame:
    rows = [{"cadaster_id": r.cadaster_id, "facility_id": f.facility_id, "minutes": round(_hav(r.lat, r.lon, f.lat, f.lon) * 1.3 / 40 * 60, 1)}
            for r in cad.itertuples() for f in fac.itertuples()]
    return provenance(pd.DataFrame(rows), "Straight-line x 1.3 detour / 40 km/h between cadaster centroid and facility (assumption)", "2026-11-21", "assumption", source_id="D01+D02")


def run() -> dict:
    cad = pd.read_csv(DERIVED / "cadasters.csv", dtype={"cadaster_id": str})
    fac = build_facilities(cad)
    cov = coverage(fac, cad)
    fac.to_csv(DERIVED / "facilities.csv", index=False)
    build_travel_time(cad, fac).to_csv(DERIVED / "travel_time.csv", index=False)
    cov.to_csv(DERIVED / "facilities_coverage.csv", index=False)
    t = cov.iloc[-1]
    return {"facilities": len(fac), "phc": int((fac.type == "PHC").sum()), "hubs": int((fac.type == "hospital_hub").sum()),
            "phc_coverage_vs_mophnetwork": float(t.coverage)}
