"""2.3 mobile units: operators and places named in 2026 reports (MSF, SAMS, UNFPA...). No routes, days or hours exist publicly, so capacity (hours per week / 40) cannot be
modelled from this file: hours stay empty and the units are NOT added to facilities.csv until a source gives hours."""
from __future__ import annotations

import pandas as pd

from .common import PROCESSED, ROOT, provenance


def run() -> dict:
    t = pd.read_csv(ROOT / "transcribed" / "mobile_units_2026.csv")
    out = provenance(t.rename(columns={"checked": "transcription_checked"}), "2026 operator reports (MSF, UNFPA sitreps, SAMS, Relief International)", "2026-08-18", "partial", "", "2.3")
    out.to_csv(PROCESSED / "mobile_units.csv", index=False)
    return {"rows": len(out), "with_hours": int(out.hours_per_week.notna().sum())}
