"""2.2/3.1 facility functional status: WHO EMRO sitreps #23 (8 May 2026) and #27 (11 Jun 2026) / #30 (23 Jul 2026) name hospitals that are closed, damaged or reopened.
The sitreps give NO location, so a facility is matched to the OSM hospital of the same NAME only (normalised name, similarity >= 0.85, unique); unmatched names are logged in
_unmatched.csv. Never matched by guess. PHCs: only national totals exist (41 closed per #23; 24 closed on 3 Aug), no names: PHC status stays unknown.
Mapping to the model's status_2026: closed -> closed; reopened -> open; damaged / partially damaged -> partial (assumption: damaged hospitals keep operating at reduced capacity)."""
from __future__ import annotations

import difflib
import re

import pandas as pd

from .common import PROCESSED, ROOT, log_unmatched

DROP = {"hospital", "governmental", "government", "public", "general", "university", "medical", "center", "centre", "al", "el", "the", "of", "and"}
STATUS_MAP = {"closed_fully_non_operational": "closed", "closed": "closed", "reopened": "open", "damaged": "partial", "partially_damaged": "partial", "partially damaged": "partial"}


def key(name: str) -> str:
    toks = [t for t in re.sub(r"[^a-z ]", " ", str(name).lower()).split() if t not in DROP]
    return " ".join(toks)


def sources() -> pd.DataFrame:
    a = pd.read_csv(ROOT / "transcribed" / "who_sitrep23_facility_status.csv").assign(status_source="WHO EMRO Lebanon sitrep #23", url="https://www.emro.who.int/images/stories/lebanon/Lebanon-Emergency-Sitrep-23-2026.pdf")
    b = pd.read_csv(ROOT / "transcribed" / "facility_functionality_2026.csv")
    cols = ["facility_name", "facility_type", "status", "status_date", "status_source", "url", "checked"]
    return pd.concat([a[cols], b[cols]], ignore_index=True)


def apply(fac: pd.DataFrame, src: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    fac = fac.copy()
    hosp = fac[fac["type"] == "hospital_hub"]
    hk = {fid: key(n) for fid, n in zip(hosp.facility_id, hosp.name)}
    src = src.assign(kname=src.facility_name.map(key)).sort_values("status_date")             # latest report wins
    matched, unmatched = [], []
    for r in src.itertuples():
        cands = [fid for fid, k in hk.items() if k and (k == r.kname or difflib.SequenceMatcher(None, k, r.kname).ratio() >= 0.85)]
        if len(cands) == 1:
            i = fac.index[fac.facility_id == cands[0]][0]
            fac.loc[i, ["functional_status", "status_date", "status_source"]] = [r.status, r.status_date, r.status_source]
            fac.loc[i, "status_2026"] = STATUS_MAP.get(str(r.status), "")
            matched.append((r.facility_name, cands[0]))
        else:
            unmatched.append(r.facility_name + ("" if not cands else f" (ambiguous: {len(cands)})"))
    return fac, pd.DataFrame(matched, columns=["source_name", "facility_id"]), unmatched


def run() -> dict:
    fac = pd.read_csv(PROCESSED / "facilities.csv", dtype={"cadaster_id": str, "facility_id": str})
    fac["status_2026"] = fac["status_2026"].fillna("") if "status_2026" in fac.columns else ""
    for c in ("functional_status", "status_date", "status_source"):
        fac[c] = ""                                                       # idempotent: rebuild from blank
    fac["status_2026"] = ""
    out, matched, unmatched = apply(fac, sources())
    log_unmatched("facility_status", "facility_name", unmatched, "named in a WHO sitrep (no location given); no unique OSM hospital of that name in the five districts")
    out.to_csv(PROCESSED / "facilities.csv", index=False)
    return {"source_rows": len(sources()), "matched_to_osm": len(matched), "unmatched": len(unmatched), "facilities_with_dated_status": int((out.status_date != "").sum())}
