"""Funded projects in Bekaa / Baalbek-Hermel (new data pack, data/raw/projects/projects_inventory.csv, 37 rows) -> data/processed/projects.csv.

Location precision: `cadaster` (a COD-AB cadaster name appears in the project text), `district` (a district name appears), `governorate` (Bekaa / Baalbek-Hermel named, no district),
`national`. Matching is by name only and conservative. `verified` is `no` for every row until a person has opened the source page and confirmed funder, implementer, amount,
dates and location (docs/RIDER_SHORTLIST.md records the result for the shortlist). Amounts are kept in their own currency; `budget_usd` is set ONLY for USD rows (no conversion)."""
from __future__ import annotations

import re
import unicodedata

import pandas as pd

from .common import PROCESSED, RAW, ROOT, provenance

DISTRICT_KEYS = {"Baalbek": ["baalbek", "baalbeck", "baalbak"], "Hermel": ["hermel"], "Zahle": ["zahle", "zahleh"],
                 "West Bekaa": ["west bekaa", "west beqaa", "saghbine", "qaraoun", "qaraaoun", "mansoura", "joub jannine", "kamed el loz", "ghazze", "kherbet qanafar", "ain zebdeh", "baaloul"],
                 "Rachaya": ["rachaya"]}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s).lower())
    return re.sub(r"[^a-z ]", "", "".join(c for c in s if not unicodedata.combining(c))).strip()


ALIASES = {"chmestar": "chmistar"}                    # spelling variants between project texts and COD-AB names (also noted in soil_sites geocode_note)
GOV_NAMES = ("baalbek-el hermel", "baalbek el hermel", "baalbek-hermel", "baalbek hermel", "baalbekhermel")


def locate(row: pd.Series, cad: pd.DataFrame) -> dict:
    raw = " ".join(str(row.get(k, "")) for k in ("districts_villages", "name", "governorate"))
    low = raw.lower()
    for g in GOV_NAMES:                                   # the governorate name is not a district mention
        low = low.replace(g, " ")
    blob = _norm(low)
    for a, b in ALIASES.items():
        blob = blob.replace(a, b)
    dist_names = {_norm(k) for k in DISTRICT_KEYS}
    cad_hits = [(r.cadaster_id, r.district) for r in cad.itertuples()
                if len(_norm(r.cadaster_name)) > 5 and _norm(r.cadaster_name) not in dist_names and re.search(rf"\b{re.escape(_norm(r.cadaster_name))}\b", blob)]
    dists = sorted({d for d, keys in DISTRICT_KEYS.items() if any(k in blob for k in keys)} | {d for _, d in cad_hits})
    gov = str(row.get("governorate", ""))
    in_region = any(k in _norm(gov) for k in ("bekaa", "beqaa", "baalbek", "hermel")) and "not named" not in gov.lower()
    prec = "cadaster" if cad_hits else "district" if dists else "governorate" if in_region else "national"
    return {"location_precision": prec, "district_list": ";".join(dists), "cadaster_ids": ";".join(sorted({c for c, _ in cad_hits}))}


def run() -> dict:
    p = pd.read_csv(RAW / "projects" / "projects_inventory.csv")
    cad = pd.read_csv(PROCESSED / "cadasters.csv", dtype={"cadaster_id": str})
    loc = pd.DataFrame([locate(r, cad) for _, r in p.iterrows()])
    out = pd.concat([p, loc], axis=1)
    out["budget_usd"] = out.amount.where(out.currency == "USD")
    out["verified"] = "no"
    v = pd.read_csv(ROOT / "data" / "registry" / "projects_verification.csv").set_index("project_id")      # per-project result of opening the source page
    out["verified"] = out.project_id.map(v.verified).fillna("no")
    out["verification_notes"] = out.project_id.map(v.notes).fillna("not checked")
    out = provenance(out, "Funded-project inventory, Bekaa / Baalbek-Hermel (desk search 2026-11-21, pages read through a summarising tool): verify before citing", "2026-11-21", "to_verify", "see source_url per row", "PRJ")
    out.to_csv(PROCESSED / "projects.csv", index=False)
    return {"rows": len(out), "precision": out.location_precision.value_counts().to_dict(), "usd_budgets_known": int(out.budget_usd.notna().sum())}
