"""3.3 official_severity: LRP 2026 Addendum (Sep-Dec 2026) district severity classes, hand-transcribed (transcribed/lrp_addendum_severity.csv, two passes).
Values are the printed CLASS (1-5), never an invented number. FSA composite is printed as text for the Severity-4 districts only; the other districts stay NaN (missing).
District names are matched to COD-AB p-codes through the crosswalk; names are mapped to project labels (El Hermel -> Hermel)."""
from __future__ import annotations

import pandas as pd

from .common import DISTRICT_LABEL, PROCESSED, ROOT, log_unmatched, provenance

SRC = ROOT / "transcribed" / "lrp_addendum_severity.csv"


def build() -> pd.DataFrame:
    t = pd.read_csv(SRC)
    d = t[t.admin_level == "district"]
    wide = d.pivot_table(index="admin_name_as_printed", columns="indicator", values="value", aggfunc="first")
    cw = pd.read_csv(PROCESSED / "name_crosswalk.csv", dtype={"pcode": str})
    a2 = cw[cw.level == "admin2"].drop_duplicates("name").set_index("name").pcode
    out = wide.reset_index().rename(columns={"admin_name_as_printed": "district_cod"})
    out["district_pcode"] = out.district_cod.map(a2)
    log_unmatched("official_severity", "admin2", out[out.district_pcode.isna()].district_cod, "district name in the LRP Addendum transcription not found in COD-AB")
    out["district"] = out.district_cod.map(lambda n: DISTRICT_LABEL.get(n, n))
    for c in ("jiaf_severity", "health_severity", "fsa_composite_severity"):
        if c not in out.columns:
            out[c] = float("nan")
    chk = d.groupby("admin_name_as_printed").checked.all()
    out["transcription_checked"] = out.district_cod.map(chk)
    out["source_date"] = "2026-09-01"
    cols = ["district", "jiaf_severity", "health_severity", "fsa_composite_severity", "source_date", "district_pcode", "district_cod", "transcription_checked"] + \
           [c for c in out.columns if c.startswith("sector_severity_")]
    return provenance(out[cols].drop(columns="source_date").assign(source_date="2026-09-01"), "LRP 2026 Addendum Sep-Dec 2026, severity maps (hand-transcribed classes 1-5, two passes)", "2026-09-01",
                      "verified", "", "S15")


def run() -> dict:
    df = build()
    df.to_csv(PROCESSED / "official_severity.csv", index=False)
    return {"districts": len(df), "fsa_missing": int(df.fsa_composite_severity.isna().sum())}
