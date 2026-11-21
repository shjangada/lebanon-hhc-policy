from __future__ import annotations

import pathlib
import re

import openpyxl
import pandas as pd

from ..io import ROOT

RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"        # real, schema-compatible datasets (the loader prefers these over data/mock)
DERIVED = PROCESSED                              # backwards-compatible alias
DISTRICT_LABEL = {"Baalbek": "Baalbek", "El Hermel": "Hermel", "Zahle": "Zahle", "West Bekaa": "West Bekaa", "Rachaya": "Rachaya"}   # project names
GOVERNORATE_LABEL = {"Baalbek-El Hermel": "Baalbek-Hermel", "Bekaa": "Bekaa"}


def provenance(df: pd.DataFrame, source: str, source_date: str, status: str, url: str = "", source_id: str = "") -> pd.DataFrame:
    """Every processed file carries is_mock (False), source_id, source, source_date, url, status (rule 2 of the ingest handoff)."""
    df = df.copy()
    df["is_mock"] = False
    df["source_id"], df["source"], df["source_date"], df["url"], df["status"] = source_id, source, source_date, url, status
    return df


def log_unmatched(source: str, level: str, names, note: str = "") -> int:
    """Append names that could not be matched to a COD-AB p-code to data/processed/_unmatched.csv (never dropped silently)."""
    names = sorted({str(n) for n in names if str(n) not in ("", "nan", "None")})
    if not names:
        return 0
    path = PROCESSED / "_unmatched.csv"
    PROCESSED.mkdir(parents=True, exist_ok=True)
    old = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=["source", "level", "name", "note"])
    old = old[~((old.source == source) & (old.level == level))]                       # idempotent: replace this source's rows
    new = pd.DataFrame({"source": source, "level": level, "name": names, "note": note})
    pd.concat([old, new], ignore_index=True).to_csv(path, index=False)
    return len(names)


def lrp_table(sheet: str, path: pathlib.Path | None = None) -> pd.DataFrame:
    """District-level table of an LRP population package sheet (cached values), indexed by clean column names."""
    path = path or RAW / "population" / "lrp_2026" / "05.-2026-lrp-population-package.xlsx"
    ws = openpyxl.load_workbook(path, data_only=True, read_only=True)[sheet]
    rows = list(ws.iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows) if r and r[0] == "Governorate" and r[1] == "District")
    hdr = [re.sub(r"\s+", " ", str(c)).strip() if c is not None else f"col{j}" for j, c in enumerate(rows[hi])]
    body = []
    for r in rows[hi + 1:]:
        if r[0] is None or r[1] is None:
            break
        body.append(r)
    return pd.DataFrame(body, columns=hdr)
