"""2.6 VASyR / MSNA: only governorate-level 'below SMEB' shares exist for Syrian refugee households (VASyR 2025); no district tables, no insurance, female-headed households are
national only. They are added to vulnerability.csv as EXTRA columns (syrian_hh_below_smeb_*_gov): they describe displaced Syrian households, not all residents, so M2 does not
use them. female_headed_hh_share, unable_to_access_care_share and no_insurance_share stay NaN (status: missing) - never filled with a national value."""
from __future__ import annotations

import pandas as pd

from .common import PROCESSED, ROOT

GOV_MAP = {"Baalbek-Hermel": ["Baalbek-Hermel", "Baalbek-El Hermel"], "Bekaa": ["Bekaa"]}


def run() -> dict:
    v = pd.read_csv(PROCESSED / "vulnerability.csv", dtype={"cadaster_id": str})
    cad = pd.read_csv(PROCESSED / "cadasters.csv", dtype={"cadaster_id": str})[["cadaster_id", "governorate"]]
    t = pd.read_csv(ROOT / "transcribed" / "vasyr_2025.csv")
    g = t[(t.geography_level == "governorate") & t.indicator.str.startswith("below_smeb")]
    vals = {}
    for gov, names in GOV_MAP.items():
        for ind, col in (("below_smeb_pct_with_assistance", "syrian_hh_below_smeb_with_assistance_gov"), ("below_smeb_pct_without_assistance", "syrian_hh_below_smeb_without_assistance_gov")):
            x = g[g.geography_name.isin(names) & (g.indicator == ind)].value
            vals[(gov, col)] = float(x.iloc[0]) / 100.0 if len(x) else float("nan")
    for col in ("syrian_hh_below_smeb_with_assistance_gov", "syrian_hh_below_smeb_without_assistance_gov"):
        v[col] = v.cadaster_id.map(cad.set_index("cadaster_id").governorate).map(lambda gv: vals.get((gv, col), float("nan")))
    v.to_csv(PROCESSED / "vulnerability.csv", index=False)
    return {"governorate_values": {k: round(x, 2) for k, x in vals.items()}, "still_nan": ["female_headed_hh_share", "unable_to_access_care_share", "no_insurance_share"]}
