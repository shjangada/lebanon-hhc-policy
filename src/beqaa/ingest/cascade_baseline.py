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


REFERRAL_SCENARIO = 0.5       # SCENARIO value, not data: no published referral completion; M5/escrow report the break-even


def build_table(long: pd.DataFrame) -> pd.DataFrame:
    """Step x group table M5 needs, with NO mock values: the reference cascade is HAUS 2024 (registered displaced Syrians, national; the 2024 rows of the long file).
    The other three groups have NO sourced baseline for Beqaa (host Lebanese rows are missing in VASyR/MSNA), so they are set equal to the reference and marked
    `basis=assumed equal to reference`: between-group gaps in the cascade are UNOBSERVABLE here and are explored only as a scenario. Referral completion = scenario value."""
    h = long[(long.group == "displaced_syrians") & (long.year == 2024)].set_index("step").value_fraction
    ref = {"p_any_anc": float(h["p_any_anc"]), "p_anc4": float(h["p_anc4"]), "p_facility_delivery": float(h["p_facility_delivery"]), "p_postnatal": float(h["p_postnatal"])}
    rows = []
    for g in ["host_lebanese", "displaced_lebanese", "registered_displaced_syrians", "unregistered_workers_est", "women_15_49"]:
        rows.append({"group": g, **ref, "p_referral_complete": REFERRAL_SCENARIO,
                     "basis": "sourced: HAUS 2024 (registered displaced Syrians, national)" if g == "registered_displaced_syrians" else "assumed equal to the sourced reference (no sourced baseline for this group)"})
    return provenance(pd.DataFrame(rows), "HAUS 2024 reference cascade (any ANC, ANC4, facility delivery, postnatal); referral completion is a scenario value", "2024-12-31", "partial",
                      "", "HAUS2024")


def run() -> dict:
    d = build()
    d.to_csv(PROCESSED / "cascade_baseline_long.csv", index=False)
    build_table(d).to_csv(PROCESSED / "cascade_baseline.csv", index=False)
    return {"rows": len(d), "verified": int((d.value_status == "verified").sum()), "unverified": int((d.value_status == "unverified").sum()), "missing": int((d.value_status == "missing").sum()), "steps": sorted(d.step.unique().tolist())}
