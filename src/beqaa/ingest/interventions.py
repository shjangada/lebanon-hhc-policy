"""3.4 interventions: the UNFPA Flash Appeal (Mar-Aug 2026) contains NO unit costs (transcribed/unfpa_cost_lines.csv: every unit_cost is empty); it gives programme-level lines only
(sexual and reproductive health USD 11M for 150,000 people; total appeal USD 25M). Nothing is derived from them. interventions.csv therefore stays MOCK: unit costs need partner
quotes (AUB speciation lab, UNFPA/WHO mobile-unit cost, CHW stipends). The appeal lines are republished here as a reference file for the funding finder / memo."""
from __future__ import annotations

import pandas as pd

from .common import PROCESSED, ROOT, provenance


def run() -> dict:
    t = pd.read_csv(ROOT / "transcribed" / "unfpa_cost_lines.csv")
    out = provenance(t.rename(columns={"checked": "transcription_checked"}), "UNFPA Flash Appeal for Lebanon (Mar-Aug 2026), programme-level lines (no unit costs)", "2026-03-01", "partial",
                     "https://www.unfpa.org/sites/default/files/resource-pdf/UNFPA%20Flash%20Appeal%20for%20Lebanon%20-%20Updated%20%28March%20-%20August%202026%29.pdf", "F007")
    out.to_csv(PROCESSED / "unfpa_cost_lines.csv", index=False)
    return {"rows": len(out), "unit_costs_found": int(out.unit_cost.notna().sum()), "interventions_csv": "stays mock (no unit costs in the source)"}
