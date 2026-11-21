"""1.4 conflict_exposure: LRP 2026 package sheet 'Conflict Incidents_adm3_Summary' (incidents since Oct 2023, per admin 3) joined by p-code.

A cadaster absent from the LRP table has no recorded incident in that table: stored as 0 with in_source=False (absence from an incident log is not a measured zero;
the column makes that visible). `incidents_per_1k` uses processed population. ACLED events (last 30/90 days) come from scripts/ingest/acled.py."""
from __future__ import annotations

import openpyxl
import pandas as pd

from .common import PROCESSED, RAW, log_unmatched, provenance


def build(cad: pd.DataFrame | None = None, pop: pd.DataFrame | None = None) -> pd.DataFrame:
    cad = cad if cad is not None else pd.read_csv(PROCESSED / "cadasters.csv", dtype={"cadaster_id": str})
    pop = pop if pop is not None else pd.read_csv(PROCESSED / "population.csv", dtype={"cadaster_id": str})
    ws = openpyxl.load_workbook(RAW / "population" / "lrp_2026" / "05.-2026-lrp-population-package.xlsx", data_only=True, read_only=True)["Conflict Incidents_adm3_Summary"]
    rows = [r for r in ws.iter_rows(values_only=True)][1:]

    def num(x):
        try:
            return float(str(x).replace("-", "").strip() or 0)
        except ValueError:
            return 0.0
    inc = pd.DataFrame([{"cadaster_id": str(int(r[3])) if r[3] is not None else None, "src_name": r[2], "src_district": r[1], "conflict_incidents": num(r[4]),
                         "incidents_to_cessation_nov2024": num(r[5]), "incidents_after_cessation": num(r[6])} for r in rows if r[3] is not None])
    inc = inc.groupby("cadaster_id", as_index=False).agg({"src_name": "first", "src_district": "first", "conflict_incidents": "sum", "incidents_to_cessation_nov2024": "sum",
                                                          "incidents_after_cessation": "sum"})
    scope = set(cad.cadaster_id)
    log_unmatched("conflict_exposure", "admin3", inc[~inc.cadaster_id.isin(set(pd.read_csv(PROCESSED / "cadasters_national.csv", dtype={"cadaster_id": str}).cadaster_id))].src_name,
                  "LRP incident row whose p-code is not in COD-AB admin 3")
    out = cad[["cadaster_id"]].merge(inc.drop(columns=["src_name", "src_district"]), on="cadaster_id", how="left")
    out["in_source"] = out.conflict_incidents.notna()
    out = out.fillna({"conflict_incidents": 0.0, "incidents_to_cessation_nov2024": 0.0, "incidents_after_cessation": 0.0})
    out = out.merge(pop[["cadaster_id", "population_total"]], on="cadaster_id", how="left")
    out["incidents_per_1k"] = out.conflict_incidents / out.population_total * 1000
    out = out.drop(columns="population_total")
    return provenance(out, "LRP 2026 population package, sheet Conflict Incidents_adm3_Summary (incidents Oct 2023 - 29 Jul 2025)", "2025-07-29", "verified",
                      "https://data.humdata.org/dataset/lebanon-population-estimates-and-displacement-figures", "D03")


def run() -> dict:
    df = build()
    df.to_csv(PROCESSED / "conflict_exposure.csv", index=False)
    return {"cadasters": len(df), "with_incidents": int(df.in_source.sum()), "total_incidents": int(df.conflict_incidents.sum())}
