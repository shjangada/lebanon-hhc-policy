"""Disaggregation + gap metrics shared by all models (principle 4).

Groups are NOT mutually exclusive: `women_15_49` overlaps the other four. Group access here reflects
*where each group lives* (spatial distribution only); legal/financial barriers are modelled in M5 via the cascade.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

GROUPS = ["host_lebanese", "displaced_lebanese", "registered_displaced_syrians", "unregistered_workers_est", "women_15_49"]
GROUP_LABELS = {
    "host_lebanese": "Host Lebanese",
    "displaced_lebanese": "Displaced Lebanese",
    "registered_displaced_syrians": "Registered displaced Syrians",
    "unregistered_workers_est": "Unregistered workers (est.)",
    "women_15_49": "Women 15–49",
}


def group_pops(pop: pd.DataFrame) -> pd.DataFrame:
    """Population of each group per cadaster. host = total - the three displaced/worker groups (floored at 0)."""
    g = pop[["cadaster_id"]].copy()
    g["displaced_lebanese"] = pop["displaced"]
    g["registered_displaced_syrians"] = pop["displaced_syrians_registered"]
    g["unregistered_workers_est"] = pop["unregistered_workers_est"]
    g["host_lebanese"] = (pop["population_total"] - pop["displaced"] - pop["displaced_syrians_registered"]
                          - pop["unregistered_workers_est"]).clip(lower=0)
    g["women_15_49"] = pop["women_15_49"]
    return g[["cadaster_id"] + GROUPS]


def by_group(values: pd.DataFrame, pop: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Population-weighted mean of cadaster-level `cols` for each group. Returns tidy (group, col, value)."""
    gp = group_pops(pop).set_index("cadaster_id")
    v = values.set_index("cadaster_id")[cols]
    out = []
    for grp in GROUPS:
        w = gp[grp].reindex(v.index).fillna(0)
        for c in cols:
            ok = v[c].notna() & (w > 0)
            val = np.average(v.loc[ok, c], weights=w[ok]) if ok.any() else np.nan
            out.append({"group": grp, "metric": c, "value": val})
    return pd.DataFrame(out)


def gap_metrics(group_values: pd.Series) -> dict:
    """Gap between best- and worst-off group. Ratio is worst/best (1 = parity)."""
    v = group_values.dropna()
    if v.empty or v.max() == 0:
        return {"abs_gap": np.nan, "ratio_worst_to_best": np.nan, "worst_group": None}
    return {"abs_gap": float(v.max() - v.min()), "ratio_worst_to_best": float(v.min() / v.max()),
            "worst_group": v.idxmin()}
