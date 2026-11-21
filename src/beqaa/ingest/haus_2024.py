"""Appendix dataset: UNHCR Health Access and Utilization Survey (HAUS) 2024: why refugee households seek care and what stops them (hand-transcribed, two passes).

National figures for refugee households known to UNHCR (mostly Syrian), telephone survey 2-20 Sep 2024 (1,448 households, 6,910 members; Bekaa = 31.5% of respondents). No Bekaa-specific
outcome tables are published. NOT a model input (no district level); used for the appendix: leading reasons for care (chronic disease, acute symptoms, maternal care) and the cost barrier.
Excludes unregistered people and anyone without a phone; self-reported; the report itself warns that the 'chronic condition' share swings with how respondents interpret the question
(21% in 2022, 12% in 2024) while hypertension / asthma / diabetes prevalence is stable. ANC/delivery/PNC rows also feed cascade_baseline_long.csv."""
from __future__ import annotations

import pandas as pd

from .common import PROCESSED, ROOT, provenance

URL = "https://data.unhcr.org/en/country/lbn"


def build() -> pd.DataFrame:
    t = pd.read_csv(ROOT / "transcribed" / "haus_2024.csv")
    t["value_fraction"] = t.apply(lambda r: r.value / 100.0 if str(r.unit).startswith("%") or "% of" in str(r.unit) else float("nan"), axis=1)
    t = t.rename(columns={"checked": "transcription_checked"})
    return provenance(t, "UNHCR HAUS 2024 report (Dec 2024), hand-transcribed (two passes for the text figures; chart values read once)", "2024-12-01", "verified", URL, "HAUS2024")


def cascade_rows() -> pd.DataFrame:
    """ANC / delivery / PNC rows in the cascade_baseline_sources schema (Syrian refugees, national, 2024)."""
    t = pd.read_csv(ROOT / "transcribed" / "haus_2024.csv").set_index("indicator")
    cit = "UNHCR HAUS 2024 (Dec 2024)"
    r = lambda step, v, unit, note, derived=False: {"step": step, "group": "displaced_syrians", "value": v, "unit": unit, "geography": "Lebanon national", "year": 2024, "source_citation": cit, "url": URL,
                                                   "page": int(t.loc[note[0], "page"]), "table_or_figure": "text bullet", "transcribed_by": t.loc[note[0], "transcribed_by"], "checked": bool(t.loc[note[0], "checked"]) and not derived,
                                                   "notes": note[1]}
    rows = [r("p_any_anc", t.loc["anc_any_share", "value"], "% of women pregnant in the 2 years before the survey", ("anc_any_share", "refugee households known to UNHCR; self-reported; 343 of 422 women")),
            r("p_anc4", t.loc["anc_4plus_share", "value"], "% of women who delivered and attended ANC", ("anc_4plus_share", "CONDITIONAL on attending ANC (not of all pregnancies); M5 treats p_anc4 as p_anc4 / p_any_anc")),
            r("p_facility_delivery", t.loc["delivery_in_hospital_share", "value"] + t.loc["delivery_other_facility_share", "value"], "% of women who delivered",
              ("delivery_in_hospital_share", "DERIVED: hospital 90% + other medical facility 7.7% (home 0.6%); sum of two stated figures"), derived=True),
            r("p_postnatal", t.loc["pnc_sought_share", "value"], "% of women who delivered", ("pnc_sought_share", "112 of 310 women who delivered and answered"))]
    return pd.DataFrame(rows)


def run() -> dict:
    d = build()
    d.to_csv(PROCESSED / "haus_2024.csv", index=False)
    return {"rows": len(d), "checked": int(d.transcription_checked.sum()), "chart_values_read_once": int((~d.transcription_checked).sum())}
