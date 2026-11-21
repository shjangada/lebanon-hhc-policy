"""3.2 soil_sites: CNRS-L/MoE post-war report (Apr 2026): Beqaa total P (Fig 2.3), total Cr (Fig 2.6) and one Pb value, hand-transcribed.

The report gives NO coordinates and lists values by village name only. Each village is geocoded to its COD-AB admin-3 cadaster by NAME (centroid = location, precision
'cadaster centroid'); villages that do not match are logged in _unmatched.csv and dropped from the located file. Values below the detection limit and the qualitative
Cu/Zn classes are not in this file (no number to report). Cr stays TOTAL Cr; the Cr(VI) share remains a parameter in M4."""
from __future__ import annotations

import re
import unicodedata

import pandas as pd

from .common import PROCESSED, ROOT, log_unmatched, provenance

SRC = ROOT / "transcribed" / "cnrs_soil_table2_3.csv"
PARAM = {"P total": "total_P", "Cr total": "Cr", "Pb": "Pb"}
# Spelling variants between the CNRS report and COD-AB names, accepted only where the variant is obvious AND the COD-AB name is unique (Rayak = Riyaq in Zahle; the others in Baalbek).
# Unresolved (not matched, logged): Bedneyil, Nabi Rchad (no clear COD-AB counterpart), Temnin (two cadasters: Temnin El Faouqa / El Tahta).
ALIASES = {"rayak": ["riyaq"], "chmestar": ["chmistar"], "ksarnaba": ["qsarnaba"], "tarayya": ["taraiya"]}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]", "", s.replace("-", " ")).strip()


def geocode(village: str, cad: pd.DataFrame) -> tuple[str | None, str]:
    names = {norm(n): c for n, c in zip(cad.cadaster_name, cad.cadaster_id)}
    for cand in [norm(village)] + [norm(a) for a in ALIASES.get(norm(village), [])]:
        if cand in names:
            hit = cad[cad.cadaster_name.map(norm) == cand]
            if len(hit) == 1:
                return hit.cadaster_id.iloc[0], ("exact name match" if cand == norm(village) else "spelling variant of the COD-AB name (verify)")
            return None, f"ambiguous: {len(hit)} cadasters named like this"
    sub = [c for n, c in names.items() if norm(village) in n or n in norm(village)]
    if len(sub) == 1:
        return sub[0], "partial name match (check)"
    return None, "no match"


def build(cad: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    cad = cad if cad is not None else pd.read_csv(PROCESSED / "cadasters.csv", dtype={"cadaster_id": str})
    t = pd.read_csv(SRC)
    t = t[t.parameter.isin(PARAM)]
    lod = t[t.value.isna()]
    t = t[t.value.notna()].copy()
    t["parameter"] = t.parameter.map(PARAM)
    geo = {v: geocode(v, cad) for v in t.site_name.unique()}
    t["cadaster_id"] = t.site_name.map(lambda v: geo[v][0])
    t["geocode_note"] = t.site_name.map(lambda v: geo[v][1])
    log_unmatched("soil_sites", "village", [v for v, (c, _) in geo.items() if c is None], "CNRS village not matched to a COD-AB admin-3 cadaster in scope")
    loc = cad.set_index("cadaster_id")[["lat", "lon"]]
    t = t[t.cadaster_id.notna()].copy()
    t["lat"], t["lon"] = t.cadaster_id.map(loc.lat), t.cadaster_id.map(loc.lon)
    out = pd.DataFrame({"site_name": t.site_name, "cadaster_id": t.cadaster_id, "lat": t.lat, "lon": t.lon, "parameter": t.parameter, "value_mg_kg": t.value,
                        "source": "CNRS-L/MoE Apr 2026, Ch. II (values); location = cadaster centroid by village name", "evidence_rung": "a",
                        "is_mock_location": False, "location_precision": "cadaster centroid", "geocode_note": t.geocode_note, "transcription_checked": t.checked,
                        "page": t.page, "table_or_figure": t.table_or_figure})
    return provenance(out.reset_index(drop=True), "CNRS-L/MoE post-war recovery report Apr 2026 (hand-transcribed, two passes); villages geocoded to cadaster centroids by name", "2025-07-01",
                      "partial", "https://cnrs.edu.lb/wp-content/uploads/2026/04/FINAL-Post-War-Recovery-Report.pdf", "S27"), lod


def run() -> dict:
    df, lod = build()
    df.to_csv(PROCESSED / "soil_sites.csv", index=False)
    return {"rows": len(df), "villages_located": int(df.site_name.nunique()), "below_detection_excluded": len(lod), "parameters": sorted(df.parameter.unique().tolist())}
