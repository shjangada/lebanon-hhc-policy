"""One-way sensitivity (tornado) of the pilot numbers to the assumptions behind them: what moves the answer, and does any single assumption flip a conclusion?

Outputs: cost per NOTIFIED case averted (M6; an upper bound on cost per illness averted), cost per household reached, red flags per year, the added load on the receiving centre and the cost per red flag found.
Each parameter is varied across a stated range with all others at their defaults; ranges are assumptions (or, for the relative risk, the published confidence interval). `swing` = high minus low
output; `flips` marks parameters whose range moves a break-even conclusion (e.g. the CHW share at which a centre exceeds the 10% load limit)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import m6_illness_averted as m6, pilot_flow as pf, start_site
from .io import load_dataset

RANGES = {  # name: (low, high, default, where it enters)
    "coverage of the district population": (0.02, 0.50, 0.10, "m6"), "transfer of the diarrhoea effect to hepatitis A / typhoid": (0.25, 1.0, 1.0, "m6"),
    "filter lifetime (years)": (0.5, 2.0, 1.0, "m6"), "household size": (4.0, 6.0, 4.6, "m6"), "relative risk (filtration, 95% CI)": (0.41, 0.60, 0.50, "m6"),
    "CHW months per site": (1, 12, 6, "m6"),
    "share of settlement people reached": (0.2, 1.0, 0.5, "flow"), "screened share": (0.2, 0.9, 0.5, "flow"), "symptomatic / positive rate": (0.05, 0.40, 0.15, "flow"),
    "share handled by CHWs": (0.3, 1.0, 0.8, "flow"), "referral completion": (0.2, 1.0, 0.5, "flow"), "spare share of centre capacity": (0.02, 0.40, 0.20, "flow"),
}
FLOW_KEYS = {"share of settlement people reached": "coverage", "screened share": "screened_share", "symptomatic / positive rate": "positive_rate", "share handled by CHWs": "chw_share",
             "referral completion": "completion", "spare share of centre capacity": "spare_share"}


def _top_site():
    r = start_site.score()
    t = r.iloc[0]
    dp = load_dataset("population").df.merge(load_dataset("cadasters").df[["cadaster_id", "district"]], on="cadaster_id").groupby("district").population_total.sum()
    return t, float(dp[t.district]), r


def cost_per_case(vals: dict, t, dpop: float) -> float:
    s = m6.simulate(t.district, dpop * vals["coverage of the district population"], dpop, "filtration", vals["transfer of the diarrhoea effect to hepatitis A / typhoid"], n=800,
                    chw_months=vals["CHW months per site"], life=vals["filter lifetime (years)"], hh_size=float(vals["household size"]), rr_point=vals["relative risk (filtration, 95% CI)"])
    return s["cost_per_case_averted_median"]


def load_share(vals: dict, t, ranked: pd.DataFrame) -> float:
    q = {FLOW_KEYS[k]: vals[k] for k in FLOW_KEYS}
    sites, cent, tt = pf.inputs_for(ranked, 8)
    ppl = dict(zip(sites.cadaster_id, sites.settlement_people_2016))
    rf = {c: pf.funnel(n, q).set_index("stage").people["red flags referred"] for c, n in ppl.items()}
    r = pf.route_red_flags(sites, cent, tt, rf, q)
    return float(r.added_load_share.max()) if r.added_load_share.notna().any() else 0.0


def tornado(output: str = "cost_per_notified_case") -> pd.DataFrame:
    t, dpop, ranked = _top_site()
    base = {k: v[2] for k, v in RANGES.items()}
    f = (lambda v: cost_per_case(v, t, dpop)) if output == "cost_per_notified_case" else (lambda v: load_share(v, t, ranked))
    where = "m6" if output == "cost_per_notified_case" else "flow"
    b0 = f(base)
    rows = []
    for k, (lo, hi, d, w) in RANGES.items():
        if w != where:
            continue
        a, b = f({**base, k: lo}), f({**base, k: hi})
        rows.append({"parameter": k, "low_value": lo, "high_value": hi, "default": d, "output_at_low": a, "output_at_high": b, "swing": abs(b - a), "baseline_output": b0})
    return pd.DataFrame(rows).sort_values("swing", ascending=False).reset_index(drop=True)


def summary() -> dict:
    c, l = tornado("cost_per_notified_case"), tornado("load")
    return {"cost_per_notified_case_baseline": float(c.baseline_output.iloc[0]), "cost_range_over_all_one_way_runs": (float(min(c.output_at_low.min(), c.output_at_high.min())), float(max(c.output_at_low.max(), c.output_at_high.max()))),
            "largest_cost_driver": c.parameter.iloc[0], "load_baseline": float(l.baseline_output.iloc[0]), "load_max_over_all_one_way_runs": float(max(l.output_at_low.max(), l.output_at_high.max())),
            "any_run_breaches_10pct_load_limit": bool(max(l.output_at_low.max(), l.output_at_high.max()) > pf.LOAD_LIMIT),
            "conclusion_flips": bool(min(c.output_at_low.min(), c.output_at_high.min()) < 20.03)}      # does any single assumption bring the cost per notified case below one primary-care visit?
