"""2.10 cascade baseline: sourced starting rates for the maternal care cascade (long format: one row per step x group x source). The model's M5 needs a complete step x group
table; published values cover only some steps and groups (e.g. VASyR national for Syrians, nothing for referral completion), so M5 keeps the mock table (flagged) until the
gaps are filled. Referral completion stays an assumption (no source found)."""
from __future__ import annotations

import pandas as pd

from .common import PROCESSED, ROOT, provenance


def build() -> pd.DataFrame:
    t = pd.read_csv(ROOT / "transcribed" / "cascade_baseline_sources.csv")
    from .haus_2024 import cascade_rows
    t = pd.concat([t, cascade_rows()], ignore_index=True)                      # HAUS 2024: Syrian refugees, national
    t["value_fraction"] = [v / 100.0 if str(u).strip().startswith("%") and pd.notna(v) else v for v, u in zip(t.value, t.unit)]
    t["value_status"] = ["missing" if pd.isna(v) else ("verified" if bool(c) else "unverified") for v, c in zip(t.value, t.checked)]
    out = t[["step", "group", "value_fraction", "unit", "geography", "year", "source_citation", "url", "page", "checked", "value_status", "notes"]].rename(columns={"checked": "transcription_checked"})
    return provenance(out, "published ANC / delivery rates (VASyR 2025, HAUS 2024, Benage 2015, AlArab 2023, MSNA 2025)", "2025-12-31", "partial", "", "VASyR/Benage/AlArab")


def run() -> dict:
    d = build()
    d.to_csv(PROCESSED / "cascade_baseline_long.csv", index=False)
    return {"rows": len(d), "verified": int((d.value_status == "verified").sum()), "unverified": int((d.value_status == "unverified").sum()), "missing": int((d.value_status == "missing").sum()), "steps": sorted(d.step.unique().tolist())}
